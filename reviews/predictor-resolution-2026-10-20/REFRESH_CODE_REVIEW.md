# Publication contract and known caveats for independent review

`SegmentedCatalog.publish(..., prepare_publication=None)` now accepts a callable.
It writes content-addressed observation/index/leaf/tree/root artifacts first, then
begins SQLite IMMEDIATE transaction, inserts snapshot+membership+observations,
calls prepare_publication(self,snapshot_id), and commits only after it returns.
An exception rolls back all new SQL metadata. Callback can use the same connection
for info/observation and durably write evidence/preview files. Another connection
continues seeing the old latest. Failed attempts leave unreachable files, not a
visible generation. Existing idempotent snapshot returns early; refresh then checks
its dependent files separately. No DB schema or server process change required.

Only refresh_catalog calls reviewed_ledger, which requires exact pinned ledger raw
SHA and all resolution fixture hashes/identities. Lower-level pure transform helpers
assume a caller-supplied ledger and support synthetic regression tests; they aren't
MCP/HTTP tools. Publication CLI pins exact200/48600source. No arbitrary exclusions.
New model_id/source_sha identify transformation+ledger+originalheader; everyworld
records original identities and evidence digest. Raw game report hashes/outcomes
remain untouched. Removed checks are retained in observation provenance and old
snapshot. New overlay is a subset bound to derivative namespace, NOT a fresh audit.

The reviewed coverage method is recognized alongside predictor_viable_starts_v1
by coverage.complete_for, summarize and derive_previews. Completeness means the
predictor inventory is covered, not physical world recall. Candidate descriptions
and BDS locate match counts are not promoted to verified physical censuses.

Please critique source identity, atomicity, proof use, count derivation, source
preservation and computational cost. No tools, code edits or new game launches.
