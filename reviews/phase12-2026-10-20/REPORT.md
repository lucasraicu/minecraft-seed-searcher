# Phase 1 and 2 — stabilization and bounded CPU evidence

Date: 2026-10-20, America/Los_Angeles. User approved both phases in chat after the
read-only review and two independent High Gemini plan critiques. No public
catalog, GPU port, custom database, payment or deployment was implemented.

## Changes

- **Predictive evidence:** standalone finalist reporting no longer emits CERTIFIED
  from a heuristic or Docker readiness. Half-open 2048 window counts are separate
  from wider stronghold discovery. Unknown prediction is not failure. Output
  distinguishes injected/native prediction from observed game evidence, whose
  build/artifact remain null until actual observations exist. Backend lifecycle
  closes on owned success/failure paths. Production eligibility/scoring is unchanged.
- **Offline calibration:** bad/nonfinite/dimensionally invalid data, failed fits,
  malformed coefficient shapes and violated bounds/ratio fail closed. Training
  accuracy is named truthfully, synthetic defaults require explicit `--demo`, and
  fits remain RESEARCH_ONLY with promotion disabled. No player study or held-out
  utility validation is claimed. Terrain output labels aggregate sampled flat
  cells in a square, retaining legacy aliases without claiming contiguous land,
  exact spawn or generated habitability.
- **Backend status:** schema v2 keeps legacy scalar/launch fields and a deprecated
  empty candidates array. Candidate pages have their own endpoint. Source hash,
  PID and server-module initialization timestamp are captured once; the timestamp
  is explicitly labeled as module initialization, not an OS creation-time proof.
  Native metadata says selected_on_disk/loaded=false; child launch provenance
  remains separate. No full input manifest is transmitted on each poll.
- **Read consistency:** pagination captures run/generation under lock, performs
  the read-only count/page WAL snapshot outside the control lock, and cannot
  publish stale totals to a newer run. Scalar DB reads have a bounded busy wait;
  failures preserve counters with progressReadError/progressUpdatedAt rather than
  reporting stale saved numbers as a fresh successful observation.
- **Frontend:** request and response-body deadlines, aborts, capped retry backoff,
  semantic payload checks and run/generation guards; no automatic retry of POST
  jobs. Ambiguous POST timeouts explain that the operation may have been accepted.
  Connecting/live/stale/disconnected states retain labeled old values. Candidate
  page failures and map failures are visible; map retry and cached-map loading
  recovery work. Last-contact age advances without waiting for new responses.
- **Specifications:** docs/PROJECT_STATUS.md separates runtime, pilot contracts and
  product vision. Platform rates/sizes/latencies are unvalidated scenarios;
  Required remains a hard same-anchor predicate, separate from Preferred utility.
  Historical completion banners no longer imply a working BDS verifier or empirical
  player calibration. The four-pillar vision and three border sizes remain proposals.

## Preexisting failures and repairs

A complete pre-integration run found **7 failed, 1,230 passed** in 411.41 seconds.
No worker patch was in the primary tree during that run.

Two failures were in the count-pilot builder: current Mineshaft source has three
vector emit sites (AVX2 main/tail and portable vector) and one scalar emit; the
old generator assumed one vector and one scalar. The initial extra-helper
hypothesis was rejected after inspecting the exact function. The repair extracts
one definition, validates the supported two-/four-site layouts, and inserts cap
checks and biome qualifications at every known site. Unknown layouts still fail
closed; no production native source was edited. A fresh diagnostic binary passed
**405** reference comparisons, including **144** positive over-cap and **45**
qualified over-cap cases. Static tests cover all emitted source paths; that fresh
pilot build uses its ordinary compiler flags, not an additional AVX2 pilot run.

Five obsolete golden checks expected 311/479 while the existing dirty baseline
produced 336/484. Recovery now checks a fresh independent Python evaluation (336);
cutoff testing independently reconstructs Python score arithmetic from captured
structure/biome facts (484). Missing/corrupt/stale/valid recovery and cutoff
admissibility assertions remain; no production score table or filter was changed.

## Measured Phase 2 results

[measurements.json](measurements.json) records exact source/build/policy identity,
input digests, samples and limitations. Four threads on the shared local iMac,
three interleaved trials, fixed inputs, fresh disposable checkpoint directories.
The harness refuses an existing output directory and limits the requested work to
**74,012** seed evaluations including diagnostics/oracles. Original run artifacts:
`runs/phase12-2026-10-20-final/` (disposable checkpoints excluded from Git); report runtime was 8.59 seconds.

| Measurement | Median | Scope |
|---|---:|---|
| Native compact screening, refinement enabled | 21,818 inputs/s | Default policy; zero retained candidates |
| Durable compact pipeline | 19,418 inputs/s | Same fixed rejection cohorts; startup/drain/close included |
| Fresh positive checkpoint | 390 ms | One known seed with required Overworld palette explicitly empty |
| Positive native evaluator | 114 ms | Conditional fixture timing; not average cost per raw input |
| Positive center-search stage | 98 ms | Includes native selection/refinement on this fixture |
| Positive record reconstruction | 42 ms | Conditional Python adapter service time |
| Positive writer service | 34 ms | Includes transaction/capacity work; not pure device I/O |

Service timers can overlap (especially queue wait); do not sum them as independent
wall-time components. Background activity is uncontrolled and small differences
between refinement on/off reject arms do not establish a speedup or regression.
The four-thread rates are not comparable to historical 34-thread figures.

Eight signed-boundary/fixed seeds had matching independent Python/native
acceptance (all rejected under default policy). Fifty-one synthetic centers had
exact independent score/tie parity, including domain/window boundaries. Coarse,
hierarchical and full-fine synthetic ranks obeyed their declared bounds. Three
fresh relaxed-positive checkpoints matched the independent Python coarse-grid
center/score at (-480,0), 336 points; resumed invocations committed zero additional
inputs. The complete regression suite separately exercises broader center parity,
rollback/idempotent retry, crash/recovery and deterministic behavior.

The positive fixture persisted about 289 KB of seed/anchor JSON. Its ~2.3 MB
checkpoint includes schema/startup/state overhead; neither is a production catalog
record-size estimate. Three repetitions of one seed do not measure diverse-world
accepted throughput. Default-blueprint positive recall, actual generated-world
accuracy, preference quality and complete public extraction remain unmeasured.

**Decision:** preserve SQLite and current predictor semantics. These observations
do not justify a storage-engine rewrite or fleet speed forecast. Center work and
record reconstruction merit representative positive-cohort profiling before a
later optimization proposal. CPU catalog extraction/summary/query design is the
next separately approved product step; the existing personal rejection funnel
must never silently become the public admission policy.

## Worker provenance and Codex integration

[workers.json](workers.json) records the three successful isolated coding tasks:
`d3e3ccf38827` (evidence), `5a3257ab3dce` (telemetry), `c8f303db26d4` (frontend).
All used `gemini-3.8-flash-high --effort high`, exited 0 with nonempty provider
SUCCESS, no denied actions, validated ownership and coordinator-rerun checks.
Codex checked each target against its dirty snapshot baseline before integrating
files, preserving unrelated edits. Codex then fixed actual TypeScript build
compatibility, bounded metadata, legacy endpoints, stale DB reporting, malformed
payload handling, body deadlines, run races, stalled page-poll recovery and tests.

Additional task `f362223e0a6e` timed out with no accepted patch; Codex performed the
diagnostic builder repair. No permissions were broadened and no accounts changed.
The earlier plan critiques remain in the operational handoff.

## Verification and deployment state

Final full-suite result: **1,274 passed, no failures or skips**, in **410.94 seconds**.
The pre-integration failures above are all resolved; raw baseline/final logs are
retained in the private MCP installation, and verification.json records hashes.
Focused evidence/backend/safety checks: **48 passed**; integration web/control/
Top-K/recovery checks: **52 passed**; fresh count-pilot checks: **7 passed**.
Network contracts: **18 passed**, including a transport ignoring abort, a stalled
body, invalid JSON/status/page, recovery and stale run/generation rejection.
Actual telemetry component rendering: **4 states passed**, including a finite
single-point history. Interactive browser behavior was not separately exercised.
TypeScript/Vite production build passed to an isolated `/tmp` directory; no live
frontend deployment or running-server restart was performed. Oxlint returned 0
with two MapCanvas hook/DOM-cache warnings; no rules were disabled or weakened.

Existing source edits, current native extensions, frozen diagnostic artifacts,
checkpoints and original web process are preserved. Changes are uncommitted; no
push, reset, stash, clean, main-branch merge, BDS world generation or large scan
was performed. Applying the new backend to the running service requires a later
controlled restart when the user is ready; new code is not claimed to be live.
