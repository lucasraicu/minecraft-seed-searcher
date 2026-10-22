# Reviewed catalog corrections

This page describes the historical per-start correction transformation. The
later [native correction report](../../reviews/predictor-resolution-2026-10-20/ENGINE_REPORT.md)
records a separate native-based refresh. The current
[generalization audit](../../reviews/generalization-validation-2026-10-20/PLAN.md)
is testing that model on new seeds, including rejected candidates; it has found
over-rejections that require further diagnosis. The ledger and older snapshots
retain their original meaning. Neither transformation certifies an exhaustive
structure count or authorizes broader exclusions.

The current correction path is an offline transformation of one pinned research
snapshot. It is separate from the native prediction algorithm. Only the reviewed
ledger at `reviews/predictor-resolution-2026-10-20/ADJUDICATIONS.json` is accepted,
with exact source generation, seed, build/settings, observation and proof hashes.
It excludes one village start and one outpost start on seed -3509659830737203357.

Inspect first:

```sh
.venv/bin/python scripts/catalog_correct.py --root /path/to/dedicated/catalog
```

This validates the ledger/proof bundle and source population, then describes the
proposed exclusions. It performs no extraction or game run. `--execute` publishes
a new immutable research generation; it never mutates the original generation.
Execution is capped at 600 seconds and 4 GiB RSS. Source files must remain stable
through publication. A newer unrelated generation blocks stale publication.

The transformation fingerprints its dependencies, adjudication ledger and original
header. Every derivative observation records original world/observation/snapshot
and evidence identity. Removed locate checks stay in its provenance and the old
audit. Retained checks keep their original outcomes, verifier and raw report hashes.
A rebound audit does not mean BDS reran the new inventory.

Only the affected world gets recomputed geometry. The other 199 worlds preserve
their exact numeric summaries with new identity metadata. This requires no GPU,
custom database or server restart. Original favorites and snapshot-pinned queries
remain reproducible. A plain reload selects the latest catalog generation; an old
shared link continues using its pinned historical snapshot.

Dependent evidence files and product previews are written, fsynced and read back
inside the publication readiness callback before the SQLite metadata transaction
commits. Another reader sees the previous generation until COMMIT. A failed or
killed writer leaves no visible new generation. Unreachable immutable files may
remain after failure and can be reused by an identical retry; do not delete files
from a serving root as ad hoc cleanup.

`predictor_viable_starts_reviewed_exclusions_v1` means the original predictor
inventory with explicit reviewed exclusions. Its coverage is not physical-world
recall. A 27-entry list whose 27 coordinates match BDS locate commands still is
not an independently exhaustive physical census. Native cave boundaries and the
general village/outpost rejection rule remain unresolved; do not turn these two
specific adjudications into a global Ancient City, height or terrain filter.
