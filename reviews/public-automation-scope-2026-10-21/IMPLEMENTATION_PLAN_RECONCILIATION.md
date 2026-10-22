# Implementation-plan review

2026-10-21. User accepted the simplified product scope and requested a clear,
specific plan. Deliverable: `PUBLIC_CATALOG_AUTOMATION_PLAN.md` at repository root.
Only documentation changed. No application tests, native builds, benchmarks,
BDS runs, seed campaigns or service restarts were performed for this writing task.

## Actual independent review

Task `699be7c200b3` succeeded. Model `gemini-3.8-flash-high`, reasoning `high`,
exit0, provider SUCCESS, nonempty response beginning PLAN_REVIEW, denied_actions[],
changed_files[], checks[]. Usage22,384 total tokens (15,969input/6,415output;
reported thinking5,375). Response and metadata are in
IMPLEMENTATION_PLAN_REVIEW.json. This was one bounded, tool-free plan critique.

## Reconciliation

1. **Record radius vs border:** the draft already separated fixed product circles
   from player borders. The review's assumption of border-limited extraction is
   false: current observations cover[-5120,5120), and coverage is checked. Added
   that exact envelope and independent outlier enrichment to make the distinction
   explicit. No redundant per-border world extraction is introduced.
2. **600-second budget:** rejected the suggested reset-on-progress watchdog. That
   would change a real total resource limit into potentially much longer work.
   Retained the explicit total budget and clarified100worlds is an upper bound;
   budget exhaustion pauses automatically. No measured claim that100worlds with
   new products will fit600seconds. Capacity expansion is a later measured choice.
3. **Dense tile budget:** accepted a concrete proposed bound of64 new64x64 tiles
   per world/evaluation revision, shared across products/height/dimension/retries.
   Budget-exhausted remains pending. Added coarse four-height record sampling and
   fair deterministic product scheduling; no gate based on missing coarse hits.
4. **Negative coordinate parity:** accepted the concern, chose the smaller change:
   project once in Python and pass coordinates to existing native APIs. Added
   negative-boundary tests. No new C arithmetic helper or predictor rewrite.
5. **Replay of pruned losers:** accepted. Receipts retain identity, descriptor,
   scopes/anchors/revisions and completed refinement progress. Re-extraction
   requires the pinned runtime; inability to replay is visible and prevents an
   all-population rebuild claim.

Codex additionally clarified per-feature coverage so a pending stronghold cannot
block an otherwise ready product, bound biome-family witnesses to the existing
surface/cave height roles, and specified the opt-in sweep control and separate
public lifecycle. These are focused contract clarifications, not implemented code.

## Verification of the written plan

Inspected current source for v1 sampling, queue limits, before-personal handoff,
refinement tile limits, family mappings/height roles, existing UI/build entrypoints
and native/summary boundaries. Reconciled live processes77988(personal3000),
77098(catalog3001),77100/77101(query),65292(Vite5173); no processes altered.
The inherited dirty workspace was preserved. Checked the16preset definitions,
17launch/5deferred record accounting, additive8feature count and membership arithmetic
(83,944 +6,000 +10,000 +4,000 +1,700 =105,644). No runtime result is claimed.

Product scope acceptance is recorded. Additional numeric defaults in the document
are explicitly proposed choices, not fabricated prior approvals. Current user
request was to write the plan; implementation has not started.
