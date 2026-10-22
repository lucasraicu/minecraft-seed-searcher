# BDS storage regression fixtures

Frozen evidence from two owned, stopped BDS 1.26.52.3 worlds. `manifest.json`
records hashes and sizes of 12 data files; this README is explanatory only.
Reports, console logs and settings are retained alongside raw Data3D exports,
point comparisons, the frozen cases and an independent decoder oracle.

Seven raw records contain 29 packed, 52 uniform and 87 unknown sections. The
oracle checks all 4,096 block IDs in each populated section using the separately
reviewed Amulet Core 1.9.25 decoding arithmetic. Hashes detect changes, not source
authenticity. Numeric IDs retain the saved-world namespace.

Only 27/54 sampled positions have stored values; all other positions remain
unknown. Locate responses do not certify physical structure completeness.
See [the report](../../../reviews/storage-bds-verification-2026-10-20/REPORT.md)
and [replay instructions](../../../docs/catalog/BIOME_STORAGE_VERIFICATION.md).

Offline regression command:

```sh
.venv/bin/python -m pytest -q tests/test_bedrock_biome_storage.py tests/test_predictor_storage_probe.py tests/test_predictor_targeted_bds.py
```
