# Rescore and export recovery

Implemented in `src/seed_search/realm/reports.py`, with diagnostic revision status added to `store.py` and deterministic coverage in `tests/test_realm_report_recovery.py`.

## Rescore contract

`rescore(store, policy, *, batch_size=256, progress=None)` validates a weight-only policy before mutation and commits at most one bounded batch of record updates plus its cursor per transaction. The saved `rescore_revision` contains `id`, `number`, `status`, `phase`, `candidate_cursor`, `variant_cursor`, full `policy`, `policy_sha256`, and committed candidate/variant counts. An interrupted revision resumes only with the same policy. A completed same-policy call starts a new revision and visits all records, including subsequently inserted anchors and centers. Baseline identity and completed coverage remain intact, and prediction/actual nested views retain separate evidence and metrics.

`ensure_score_revision_complete(store)` rejects incomplete revisions. Public ranking and export enforce this check inside an independent read-only SQLite snapshot; root-owned CLI guards use the same helper for generation/resume commands. Status and rescore remain available. Scanner and rescore share a nonblocking run lock. No generation queries are performed.

## Publication contract

Export writes the complete baseline/V1/V2 JSONL and CSV set, summary JSON/Markdown, and SHA256 manifest under `results/.generations/export-<id>`. Files and directories are synced before an atomic replacement of the `results/current` symlink. Stable `results/baseline.jsonl` and the other existing paths resolve through this pointer. Existing flat exports migrate without changing their bytes. Previous generations remain intact after injected write/publication failures before the pointer switch.

The manifest records the source identity hash, committed seed count, record counts, score revision, and hashes/sizes of all generated files. Multi-file consumers must resolve `current` once and use that pinned generation path to avoid mixing separate opens across a later publication. The separate SQLite snapshot never commits a caller transaction and holds one coherent read view across every file.

## Verification

Final focused command:

```text
.venv/bin/python -m pytest tests/test_realm_report_recovery.py tests/test_realm_cli_reports.py tests/test_realm_store.py tests/test_realm_terrain.py -q
53 passed in 1.73s
```

Recovery tests cover candidate/variant phase interruption, reopen/resume, rejection of a different policy, batch rollback with cursor rollback, repeated same-policy rescoring after new records, generation prohibition, independent nested views, CLI guards, midstream export failure, pointer failure, full-set manifest hashes, flat-export migration, and snapshot isolation without committing caller writes.

An earlier broader run observed a separate root-owned verification-selection expectation failure (`test_cli_persists_selection_reasons_without_generation`: expected four selected, received zero after eligibility filtering). That test and CLI were not modified here and the failure was reported to root.

## Limits

Rescore uses revisioned in-place records, not a second full dataset. Direct diagnostic getters or external SQL writers bypass the ranking/generation guard; supported guarded commands prevent ambiguous mixed-score views. Previous and unpublished generation directories are retained; garbage collection is not implemented. A failure after the atomic pointer replacement can leave the new complete generation published even if later directory syncing reports an error. Long exports hold a SQLite read snapshot and can grow WAL under concurrent writes; large concurrent export performance is unmeasured. No native benchmarks or BDS launches were run for this change.
