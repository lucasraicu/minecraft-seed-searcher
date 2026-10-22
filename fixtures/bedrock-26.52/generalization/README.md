# Frozen BDS generalization evidence

These fixtures preserve the bounded 24-world audit, not an exhaustive census or
an all-seed accuracy guarantee. See the [audit report](../../../reviews/generalization-validation-2026-10-20/AUDIT_REPORT.md)
and [per-type coverage](../../../reviews/generalization-validation-2026-10-20/COVERAGE_AND_CLAIMS.md).
Pinned game build: BDS 1.26.52.3. Required scope: Overworld and Nether.

From the repository root, run the portable checks without Docker, BDS, Google
workers or new seed generation:

```sh
.venv/bin/python -m pytest -q tests/test_generalization_audit.py tests/test_generalization_biome_probe.py tests/test_generalization_structure_probe.py tests/test_generalization_report.py tests/test_generalization_coverage.py tests/test_generalization_evidence.py
```

The 87 checks validate the audit helpers and replay real saved evidence. They do
not rebuild or integrate a predictor correction. The archive test reads bounded
regular files in memory and verifies archive/member hashes; it does not extract
untrusted paths onto the filesystem.

- `audit-evidence-v1.tar.gz` and its manifest retain 163 checksummed files: frozen
  seed/position predictions, 24 default-game reports, settings, observers and raw
  logs, failures, seven Beta-copy attempts and two stable-API copied-world rechecks.
  Failed/loading observations remain unknown, not seed rejection or absence.
- Supplementary `obsolete-runtime` comparisons deliberately remain historical.
  Only `correct-runtime` comparisons apply to the stated isolated native binary;
  they are post-observation reanalysis, not another blind validation cohort.
  The original 3,411 frozen predictions independently replay with zero differences.
- The 137 Beta-copy points establish scoped biome/type membership observations.
  Multiple member blocks do not count distinct instances; Beta settings are not
  evidence of equivalence to default generation.
- The 46 stable-API recheck points target already discovered mismatches. They
  diagnose a local failure and do not estimate population accuracy.
- `stored-ceiling-witness-v1.json` and its checksum retain the exact saved chunk
  record and 21 API observations. Numeric biome-ID associations are local to that
  record/world; its last explicit Y95 plane is not a universal engine limit.
- `positive-counterexamples.json` is the earlier six-case milestone; later audit
  evidence includes 14 BDS-exact rejected village references and three independent
  structure-discovery omissions. Preserve the earlier milestone as history.
- `exact-y-completed-audit-prototype-v1.json` and its checksum add the 14-case
  isolated prototype results, probe source/output and integer-parity record.
  This supplements the audit archive; it is not an integrated production patch.

No exact generated totals, recall, physical absence or rare-density guarantee can
be inferred from these point/reference methods. General native changes and public
catalog refresh remain separate reviewed work.
