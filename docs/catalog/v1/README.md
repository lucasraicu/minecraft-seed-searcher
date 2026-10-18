# Proposed catalog contracts v1

Design authority: [PUBLIC_CATALOG_SYSTEM_SPEC.md](../../../PUBLIC_CATALOG_SYSTEM_SPEC.md). These artifacts describe the proposed implementation; none is loaded by the current application, and all runtime/billing activation flags remain false.

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

The full search UI, public extraction, GPU pipeline and payment adapter remain future implementation. The local vendor spawn-timing experiment is recorded under [reviews/catalog-system-spec-2026-10-17](../../../reviews/catalog-system-spec-2026-10-17/spawn-timing.json); it establishes neither spawn accuracy nor production performance.

The [independent spawn audit](../../../reviews/spawn-validation-2026-10-17/README.md) subsequently found all 108 estimates within 11.32 horizontal blocks of the default spawn on BDS 1.26.52.3. This supports the planned Estimated spawn anchor; actual-player placement and complete-record cost remain unvalidated, and runtime flags remain false.
