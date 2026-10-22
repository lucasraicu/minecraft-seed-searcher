# CPU catalog reference

The additive practical accuracy extension is documented in
[ACCURACY.md](../../../docs/catalog/ACCURACY.md). The v1 contracts below remain frozen;
per-snapshot world-spawn modes and exact-scope refinement use separate versions.

Source-tree developer reference, not a public service. Predictions are not
generated-world certification. Product registry/billing flags remain disabled.

`models`, `registry`, `request`, `capabilities` and `geometry` define the frozen
developer contracts. `extract` obtains14 Overworld start inventories plus one
Y63/stride64 biome lattice across[-5120,5120). There are no personal floors.
Unknown/missing features cannot pass Required or earn Preferred utility. The
initial full-envelope adapter marks incomplete feature scopes conservatively;
it does not claim arbitrary partial-tile queries or actual biome absence.

`summaries` derives81 anchors x3 border sides from those observations. `codec`
packs each layout's derived feature payload into364 bytes:352 numeric bytes and
12 completion bytes. Absolute observations are stored once, not per layout.
`query` enforces same-layout requirements, chooses a world's best eligible center
and deduplicates before TopK. Supported radii are256/512/1024; arbitrary sliders,
spawn, Nether and stronghold/basement mandatory filters are gated. Count fractions
use integer LCM720720; profile H uses a deterministic50-digit Decimal square root.
Printed score percentages are informational; ordering uses unrounded utility.

`artifacts` stores bounded, deterministic gzip JSON bundles with checksums;
`store` manages a separate `catalog.sqlite`, packed payloads and immutable
snapshot manifests that bind payload hashes and policy/registry revisions.
Metadata publication follows durable file publication. Reader startup never
deletes another writer's staging files. Offline orphan garbage collection is not
implemented; unreferenced artifacts can remain after failures. No shared-network
SQLite WAL or custom durable database engine is used.

From the repository root, using the existing environment:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/catalog_reference.py build \
  --output /absolute/fresh/reference-run --threads 1 --seconds 300
```

This explicitly runs at most two predetermined seeds under a cumulative durable
wall budget,4GiB child-RSS watchdog and1GiB output watchdog. Default native engine
is serial; threads>1 requires an already compatible OpenMP build. The script does
not rebuild binaries. RSS/output checks are polling limits, not instantaneous
kernel quotas. Native calls run in owned supervised child processes. A parent
crash consumes the outstanding budget reservation; this conservative prototype
does not automatically refund crashed work. Failed features remain explicit.

Resume the same controls/source/build without launching completed seeds again:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/catalog_reference.py build \
  --output /absolute/existing/reference-run --threads 1 --seconds 300 --resume
```

Use `report.json` for the immutable snapshot ID. Query JSON follows
`docs/catalog/v1/request_schema.json`, with `game_build_id` explicitly labeled
`research:<model_id>` from the observation identity; exact public game versions
remain unaccepted. Set `catalog_snapshot_id` to that report's snapshot ID.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/catalog_reference.py query \
  --catalog /absolute/reference-run/catalog --request /absolute/request.json --limit 5
```

`CatalogStore.backup(fresh_destination)` makes and validates a recoverable
metadata/artifact copy. Run checks with `.venv/bin/python -m pytest tests/catalog`.
The independent220-case oracle derives its facts from raw coordinates, not the
packed summaries. Full reference reads intentionally verify/load raw observations;
that cost is not representative of a future cached metadata-only serving index.

The next bounded validation stage adds `ingestion`, `retention`, `scoring`,
`view` and `evaluation`. Ingestion predeclares100 seeds independently of personal
search, saves per-world receipts and feature checkpoints, and supports matching-
control resume. Its10-world preflight and remaining90 share one15-minute
extraction budget. The full validation job has a cumulative30-minute budget,
4GiB aggregate-RSS watchdog and2GiB output watchdog. Crashed reservations are
conservatively charged; a retry never silently resets the allowance. Child work
starts only after its ownership lease is durable. Supervisor lifeline closure
requests cleanup; process-death tests cover saved-progress and SQLite publication
boundaries. These are polling/process-recovery checks, not power-loss certification.

`retention` evaluates6,931 fixed objective lists from the existing policy, picks
each world's best qualifying anchor before bounded TopK, and supports exact
partition merges with policy/build binding. Pins and the stable-hash reference
sample are independent of personal requirements. This stage stores selections
as derived views; it does not evict the unpruned reference observations. An
independent global-sort oracle checks memberships. Reduced-cap experiments and
explicitly fabricated oversubscription data exercise selection loss; results on
100 worlds cannot establish production-capacity recall.

`SnapshotView.from_snapshot(store.snapshot(snapshot_id))` validates raw data once
and defensively freezes summaries for repeated queries. The functional `query`
entry point remains available. Both use the same Required/Preferred and anchor
semantics. `evaluation` freezes200 requests before examining selections and reports
nonempty preservation, unique-world top10 recall and score regret. Empty-reference
queries are excluded from those denominators; a nonempty reference with no retained
match receives regret1. A selection that retains every world is explicitly labeled
non-discriminating.

The separate validation command preserves the original two-world CLI's cap:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python scripts/catalog_validate.py run \
  --output /absolute/fresh/approved-validation-run
```

Add `--resume` for the same run and unchanged source/build/controls. Output includes
the controls, frozen requests, receipts, selections, query metrics and restore
result. The command neither deploys a service nor starts an open-ended campaign.

This prototype loads proposed contracts from the source checkout, not installed
wheel resources. Its dictionaries are developer records, not a hostile multi-
tenant storage boundary. Per-artifact size is capped at16MiB; manifests are flat
and intended for the small reference, not millions of worlds. There is no public
API/UI, physical retention eviction, large campaign, paid entitlement or GPU implementation.
