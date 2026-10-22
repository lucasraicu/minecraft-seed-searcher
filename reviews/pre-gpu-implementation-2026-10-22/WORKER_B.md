# B — Approved ingestion optimization

Use explicit High reasoning. Implement package B from the approved readiness plan.
Owned ONLY: src/seed_search/catalog/harvest_native.py, extract.py, summaries.py,
refinement_worker.py, and new tests/catalog/test_ingestion_optimization.py.
Do not edit ingestion.py, models.py, registry.py, artifacts.py, native or any other
file. No recursively delegated tasks. No shell commands from model: use scoped
file readers/edits; coordinator executes tests. Do not send completion notification.

Read checkpoint/extraction and summary call flow. Profiling measured 814MB repeated
JSON serialization for one ~8.6MB final checkpoint; 4,105 json.dumps. 22.5s extraction/
checkpoints and5.74s summaries. Full profile timings perturb deadlines. Optimize
real redundant work without dropping native work, validation boundaries, fsync,
heartbeats, leases or progress durability. Preserve checkpoint reader compatibility.
Prefer byte-equivalent canonical checkpoint encoding with one serialization rather
than hashing/dumping same object twice, and safe source-bound index reuse in summary
loops; inspect correctness rather than assuming these are sufficient. No arbitrary
batch enlargement or checkpoint frequency reduction that loses acknowledged state.
No global mutable observation caches or unbounded buffers. NativeProvider batched
sampling is optional only with exact positive/unknown/tile parity and deadline checks.

Add meaningful tests for checksum/tamper detection, resume, callback value isolation,
correct fixed-work outputs, and changed optimization boundaries. Use existing mocks
and tiny synthetic observations so tests need no native extension. No fresh seed
search/extraction or benchmark in worker. Worker time ≤900s; CPU≤180s; memory≤768MiB;
report changed files, actual checks, limitations and precise recovery replay quantum.
Return concise result, no unsupported speedup claims. Codex benchmarks independently.
