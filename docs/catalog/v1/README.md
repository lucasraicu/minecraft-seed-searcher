# Proposed catalog contracts v1

Design authority: [PUBLIC_CATALOG_SYSTEM_SPEC.md](../../../PUBLIC_CATALOG_SYSTEM_SPEC.md). These artifacts define the v1 vocabulary read by the private CPU/serving reference and Catalog tab. Public capability/billing flags remain false. The [reconciled master plan](../proposals/Public_Catalog_Master_Plan.md) organizes the four product pillars and later stages without changing this registry, request schema or score semantics.

Separate private product registry and CPU handoff now implement the four entry
points without changing these query-v1 artifacts. See
[four-pillar usage and recovery](../FOUR_PILLARS_AND_HARVEST.md). Sweet16 and named
records retain evidence gates; research circles have their own explicit scope.

| File | Defines |
|---|---|
| [feature_registry.json](feature_registry.json) | Eight UI categories, 23 proposed filters, evidence semantics, roadmap gates |
| [ui_presets.json](ui_presets.json) | Visible editable preference rows for every category |
| [public_policy.json](public_policy.json) | Personal isolation, exactly three borders, anchors, retention capacities, scoring profiles, quotas |
| [request_schema.json](request_schema.json) | Canonical query vocabulary; runtime capability checks remain additional |
| [example_request.json](example_request.json) | Illustrative query with placeholder build and snapshot IDs |
| [storage_layout.json](storage_layout.json) | Absolute coordinates, tiled observations, binary summary arrays, index segmentation |
| [catalog_schema.sql](catalog_schema.sql) | Executable reference control/pilot SQL; never applied to the personal database |
| [build_contracts.py](build_contracts.py) | Deterministically generates the six JSON documents |
| [validate_spec.py](validate_spec.py) | Contract/reference consistency checks, not production catalog tests |

From the repository root:

```sh
python3 docs/catalog/v1/build_contracts.py
python3 docs/catalog/v1/validate_spec.py
```

The CPU research extraction/coverage/summary/query reference is implemented in
[`src/seed_search/catalog/`](../../../src/seed_search/catalog/README.md), with a
bounded two-seed CLI and a separate100-world validation harness for ingestion,
fixed retention, immutable read views and recovery. [Measured results](../../../reviews/catalog-validation-2026-10-20/REPORT.md)
apply to the declared developer corpus. It uses a separate runtime SQLite schema; the illustrative
SQL above remains a design reference and is never applied to the personal store.
The separate [private pilot](../PRIVATE_PILOT.md) now adds segmented serving, a query/detail
API and Catalog UI with200 worlds/48,600 layouts; [validation](../../../reviews/catalog-private-pilot-2026-10-20/REPORT.md)
records browser QA as deferred and wider evidence gates as open. Four-pillar
entry points and an opt-in CPU campaign handoff with explicit draining are now
implemented privately. Attachment to the running scan, production-scale public
ingestion, GPU pipeline and payment adapter remain future work. The local vendor spawn-timing experiment is recorded
under [reviews/catalog-system-spec-2026-10-17](../../../reviews/catalog-system-spec-2026-10-17/spawn-timing.json);
it establishes neither spawn accuracy nor production performance.

The [independent spawn audit](../../../reviews/spawn-validation-2026-10-17/README.md) subsequently found all 108 estimates within 11.32 horizontal blocks of the default spawn on BDS 1.26.52.3. This supports the planned Estimated spawn anchor; actual-player placement and complete-record cost remain unvalidated, and runtime flags remain false.
