# Independent High reviews and Codex reconciliation

Two independent, tool-free critiques reviewed the preserved
[draft](DRAFT_PLAN_REVIEWED.md) and audit context. Both used
`gemini-3.8-flash-high --effort high`, finished successfully with process exit 0,
reported no denied actions, and made no edits or test claims. Their actual queue
results, launch configuration, responses and usage are preserved:

- Correctness/recovery: `1ff842502952`, [result](GEMINI_CORRECTNESS_REVIEW.json).
- Performance/storage: `c3dfcdfb5058`, [result](GEMINI_PERFORMANCE_REVIEW.json).

Reported total usage: 41,948 tokens. There is no account/quota pause; no remaining
quota estimate is available. Codex inspected both responses and independently
reconciled them against the source, existing regression evidence and measured
profiling limitations. These critiques are not independent execution of tests.

## Accepted corrections

1. Decouple the GPU numerical/admission specification and isolated one-device proof
   from serving optimization. Both tracks start from a restorable CPU reference;
   sustained ingestion and recovery gate high-volume integration, not isolated math.
2. State public admission explicitly: a personal cutoff must not discard useful
   candidates within the declared public evaluated population. Public sampling or
   an independent branch precedes personal rejection.
3. Specify recovery replay bounds in work and time, and pin views/cursors to the
   original immutable snapshot and matching view generation during publication.
4. Separate broad saved-fact correctness replay from the small extraction timing
   cohort. Reuse reserve mechanics tests; do not require a huge CPU population to
   prove an isolated GPU kernel.
5. Confirm actual target GPU hardware. This host's AMD Vega 56 is verified; future
   NVIDIA/CUDA hardware and access are unverified.
6. Bound caches, aggregate owned RSS and total new logical disk, including staging,
   indexes, input copies, WAL, temporary files and reports. No old budget is reset.
7. Keep the 0.48ms SQL lookup labeled as an incomplete prototype. The illustrative
   250ms board target must pass the complete guarded API and is not a p95 or SLA.
8. Keep engine selection conditional and outside the isolated GPU critical path.
   Physical writes and serialized JSON text are distinct measurements.

## Recommendations narrowed or rejected

| Worker recommendation | Codex disposition and reason |
|---|---|
| Only prune a seed after all 7,543 public thresholds fail | Scope the invariant to the declared evaluated public sample. Independent public admission is valid; this is not a mandate to evaluate all 2^64 seeds or every objective for unsampled seeds. Missing evidence cannot justify pruning. |
| Replay at most one `batch_size` | Define component-specific units first. Biome-point batches, refinement tiles and seed batches are different quantities; an arbitrary shared N is not an executable recovery contract. |
| Roll back to the last full snapshot on corrupt deltas | Reject silent loss of acknowledged observations or consumed budgets. Reconstruct a verified prefix only when the full acknowledged state is recoverable; otherwise fail closed and preserve evidence. |
| Add a mutable transaction sequence to every cursor | Immutable snapshot identity plus a bound view generation addresses torn publication while preserving the existing cursor contract. A new mutable sequence is not automatically required. |
| Extract 25–30 worlds within 600 seconds by subsampling | At about 32 seconds per measured full record, this exceeds the cap or changes the work. Use saved observations for broad correctness; keep full-work performance comparisons small and labeled. |
| Benchmark a new engine only after SQLite write-lock/B-tree failure | Too narrow. Decode/scan CPU, RAM pressure, startup, history and publication can justify a later comparison even without lock contention. Declare a target first; do not select an engine now. |
| More than 10,000 worlds necessarily exceeds RAM | Unsupported universal threshold. Layout, fact density, history and target RAM determine the working set. Label cache-resident replicas and actual out-of-memory measurements separately. |
| Require zero loss of any state | Preserve acknowledged data and budgets; explicitly bound replay of work that was not yet acknowledged. This avoids an impossible claim about all in-flight computation. |

The [final proposed plan](../../docs/PRE_GPU_READINESS_PLAN.md) incorporates these
resolutions. Its implementation boxes remain unchecked. Only this audit, plan,
navigation corrections and factual handoff were completed; no optimization,
GPU port, engine migration, personal restart or new seed/game campaign occurred.
