# Bounded migration recovery proposal — approval required

The approved 3,600-second cumulative migration allocation has 11.192 seconds
remaining at the durable checkpoint: 162 of 222 corrected worlds, 3,588.808 seconds
charged. The original full migration completed in 3,150.624 seconds, but failed
query latency and independent legacy membership parity. It has not been adopted.
Correction has used the remainder; intermediate failures and conservative crash
reservations are retained in the charged total. No allocation reset is proposed.

Request: one additional 180-second allocation, bringing the cumulative ceiling to
3,780 seconds. Keep the 4 GiB aggregate process RSS, 2 GiB aggregate output, 16 MiB
artifact, 1 MiB request, 4 MiB reply and 10-second query limits unchanged. No native
sampling, seed searches or BDS runs; no personal restart or scoring change.

Resume `scripts/reindex_catalog_biomes.py` in the existing isolated corrected root.
Convert remaining immutable projections with a bounded local process pool, retain
only eligible `catalog-summary-v1` recommended-grid payloads exactly as the existing
policy does, and merge durable per-world offers once by exact typed rank and world.
Use existing SQLite transactions, CAS, policy identities and atomic publication.
No architecture change or new worker framework. Codex owns this integration.

Before execution, test the variant legacy exclusion and durable offer round trip,
compare the bulk merge against AutomationLedger and full sorting on synthetic
cases, and resolve the narrow Gemini High source review. Store the actual approval
and incremental allocation durably, preserving the prior consumed total. Stop and
checkpoint on exhaustion; no further allocation is authorized by this proposal.

After publication, independently verify all 222 worlds, exact legacy mode payloads,
old primary preservation, atomic 2K ranks, raw observations/evaluations/history,
all nine mixed HTTP queries, row/alternative stress, paging and historic shares.
Adopt only after these checks pass. Existing public/personal services stay unchanged
until then. Expected remaining verification and adoption: 20–35 minutes after approval,
subject to measured failures. Relative complexity: small recovery change; acceptance
remains the original full release, not a partial catalog.

Gemini High critique `5f465679eadf` completed read-only, exit 0, denied actions [],
no edits/tests. Codex reconciliation: accept replacing every execution ceiling with
one explicitly approved durable total; retain the original 3600 allocation as a
separate immutable fact and do not refund conservative crash reservations. The
proposed 180 seconds is an estimate, not a completion guarantee. Existing destination
ledger contains only this pinned correction's correctly processed prefix; enforce
that prefix before using its members. Rebuilding that valid prefix is unnecessary.
Full final membership audit remains mandatory. Preserve tree/output checks rather
than relying only on new artifact bytes, which omit SQLite growth and other files.
The OS CPU limit stays bounded by remaining allocation and each child inherits it;
spawned pure-Python conversion previously exited without a CPU-limit signal.
Aggregate RSS includes the complete local process tree; pool size is eight, while
Gemini delegation remains separately bounded to four. No native calls occur here.

Independent recovery checks: two tests pass (0.36 seconds), covering 103 distinct
worlds, exact decimal/rational ranks, worse duplicate offers, real ledger equality,
independent full sorting, replay idempotence, CAS dictionary round-trip and the
original policy's legacy eligibility exclusion. Packed projection/storage nine tests
pass (6.61 seconds). These do not substitute for final 222-world/HTTP acceptance.

User approval received: "Approve additional 180 seconds" in response to the exact
bounded question. Recorded durably with correction pin and charged3588.808 seconds.
Approved ceiling3780; no additional future allocation is implied.
