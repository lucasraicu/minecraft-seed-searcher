# Split audit contract and final Codex review

## Assignment map

| Owner | Responsibility | Handoff |
| --- | --- | --- |
| Sol | Mansion profiling, preflight cost/order, scheduling, survivor-stage timing, measured optimization proposals | `sol/REPORT.md` plus raw measurements and reproduction commands |
| Gemini coordinator | Four independent discovery agents, then an adversarial verification agent | `gemini/REPORT.md` plus agent reports and verified reproductions |
| Codex | Final review of both packages, reproduction of material claims, conflict resolution, combined verdict | `codex/FINAL_REVIEW.md` and claim disposition ledger |

Execution prompts: [Sol plan](SOL_PLAN.md) and [Gemini plan](GEMINI_PLAN.md). Planning does not itself start either audit. Both teams' final results must return to Codex for review.

## Common baseline and scope

Prepared against commit `54b7d631b8bdb481894980a31be16aaa02901b18` and the production `dynamic-envelope-1664-v1` policy. At execution, verify the actual checkout and agree on one baseline. Preserve the resolved configuration, source/build identities, and input manifests in each package.

Prior evidence lives in `reviews/codex-audit-2026-10-15/`. Its findings and performance numbers are historical evidence tied to that baseline, not automatic conclusions for a changed checkout. Gemini discovery agents should complete first-pass reports before receiving those conclusions.

This assignment covers remaining audits and isolated validation. It excludes end-to-end validation, combined generation-to-persistence benchmarks, live production sweeps, BDS verification, production fixes, deployment, and automatic adoption of proposed changes. Proposed code changes remain reviewable patches in isolated copies.

Only Sol owns timed performance experiments. Both teams must coordinate benchmark-machine load. Separate worktrees prevent source collisions but do not prevent CPU, memory-bandwidth, or thermal interference.

## Minimum evidence record

Use a stable finding/experiment ID in reports, logs, patches, and raw results. Every record must identify:

- Baseline commit; resolved configuration hash; relevant source, binary, runtime, compiler, and PGO identities.
- Exact reproduction command and input provenance.
- Synthetic versus natural inputs, full64 seed/index mapping, and training/evaluation separation when relevant.
- Expected result and observed result.
- Raw evidence location and limitations.

A defect additionally needs severity, exact file and verbatim anchor, concrete numerical trigger or deterministic interleaving, and a minimal proposed fix. A performance result additionally needs all trials, timing boundaries, alternating order, paired comparison method, variability, and parity evidence.

Do not equate a functionally valid synthetic fixture with a natural-world discovery. Do not equate a matching all-reject receipt with survivor correctness, replay reconstruction with independent center selection, or lack of a reproduced race with a proof of thread safety.

## Codex final-review procedure

### C1 — Check provenance and scope

Read both packages, not only their executive summaries. Verify that they refer to the same baseline and policy and that proposed changes remain unapplied. Check whether benchmark binaries and PGO profiles match their source identities. Record missing artifacts or excluded tasks explicitly.

If a claim uses a different baseline, classify it as noncomparable until a targeted reproduction resolves the difference. Do not silently combine incompatible measurements.

### C2 — Review all important conclusions

Reproduce every P0/P1 proposed for final acceptance using its recorded trigger. Inspect diagnostic modifications to ensure they only expose the claimed condition. Verify normal inputs, error propagation, cleanup, and evidence consequences relevant to the finding.

Review P2 findings affecting resource bounds, returned results, or operational state. Re-run a targeted reproduction for any disputed or material P2. Do not rerun unrelated broad suites merely to increase test counts.

For each geometry/scoring claim, check its derivation against half-open intervals, integer events, lattice transitions, 16/8 snapping, strict/flexible floors, and the +30 monument milestone. Inspect any optional-count or ranking assumptions explicitly.

### C3 — Review performance claims

Check conditional rejection/cost measurements, cohort disjointness, instrumentation effects, host contention, PGO fairness, trial ordering, timing scope, and choice of summary statistic.

Reproduce a representative alternating pair for each finalist; repeat enough of the recorded trial protocol when noise or the claimed benefit makes one pair insufficient. Check all changed eligibility, scoring, selected-center, inventory, and receipt behavior on representative survivor fixtures and compatible natural inputs.

Keep kernel, stage, reconstruction, and writer measurements distinct. Use measured stage fractions to bound aggregate gains. If a changed control or missing provenance prevents attribution, mark the claim unresolved rather than assigning a speed-up.

Review the earlier delayed-generator proposal alongside new proposals. State whether it is already adopted, still experimental, superseded, or no longer applicable to the actual baseline.

### C4 — Reconcile independent findings

Build a disposition ledger:

| Field | Required value |
| --- | --- |
| ID | Original Sol/Gemini IDs and cross-references |
| Claim | One concrete defect or performance conclusion |
| Disposition | Accepted, rejected, unresolved, duplicate, or superseded |
| Reason | Reproduction or proof supporting the disposition |
| Evidence | Commands, source anchors, artifacts, and raw results |
| Action | Minimal proposed fix, justified experiment, or no change |

Resolve contradictions by inspecting assumptions and reproducing the disputed behavior. Neither majority agreement among agents nor agreement between models is sufficient proof. Preserve genuine unresolved disagreements.

### C5 — Deliver the final combined audit

Write:

```text
codex/
  FINAL_REVIEW.md
  dispositions.json
  reproduction-log.md
```

The final report must contain:

1. Accepted P0/P1 defects, with exact anchors, numerical triggers, and minimal fixes; otherwise `None verified`.
2. Remaining measured bottlenecks and limits of the measurements.
3. At most two strongest performance proposals, each with a reviewable diff, measured or bounded impact, correctness evidence, and adoption prerequisites.
4. Rejected proposals and unresolved claims that materially affect the conclusion.
5. A scope-specific `PASS`, `CONDITIONAL PASS`, or `FAIL` with rationale. This sign-off covers only the audited scope and cannot certify excluded end-to-end behavior or actual BDS generation.

Codex must distinguish completion of the audit from implementation of its recommendations. Finish once both packages have been reviewed and material claims have a supported disposition or an explicit evidence gap. Do not claim every possible bug or speed-up has been exhausted.
