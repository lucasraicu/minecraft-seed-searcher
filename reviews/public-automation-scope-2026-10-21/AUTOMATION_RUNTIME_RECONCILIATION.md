# Runtime review reconciliation

High c19f27c699e5 succeeded, read-only, no tests. Actual source review identified
a valid recoverability concern: commit followed by a non-resource publication
exception could continue to another world. Codex now pauses on any such committed
membership/pointer failure; startup reconciles that generation before new jobs.
OSError already paused. Crash/resume test verifies reconciliation before extraction.

Ordinary resume now preserves consumed time. A separate explicit allocate action
(only while paused and worker idle) grants a new600second budget; UI must clearly
label that action. Active resume never silently resets spend.

Rejected unsupported findings: claimed checkpoint=None is not produced by
HarvestQueue.claim (it always assigns a generation-specific path); a defensive
guard was still added for clearer injected-failure behavior. queue.heartbeat is a
bound method and extract_native calls heartbeat(job), as the existing tested API
requires. RSS bound is job.caps.rss_bytes, not the invented child_rss_bytes field;
extract_native already monitors the process tree and terminates owned children.

Per-world resource pauses are an explicit approved safety policy, not a continuity
bug: partial observations publish before pause and remain resumable. Do not remove
that safety behavior solely to increase throughput. Root budgets never reset on
progress, restart or ordinary resume. Concurrent implementation contracts remain
pending integration, not claimed verified by the read-only review.
