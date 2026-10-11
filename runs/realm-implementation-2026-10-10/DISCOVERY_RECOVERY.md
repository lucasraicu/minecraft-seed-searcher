# Seed discovery evidence and recovery

`baseline.py` now returns seed-level `discovery` with raw and viable Stronghold/Fortress observations, bounds, seed, predictor source/model/commit, saved settings, and explicit unresolved recall/absence coverage. These observations survive even when there are no anchor candidates. Existing `unresolved_discovery` retains its zero-viable-Stronghold meaning; separate `unresolved_stronghold_coverage` and `unresolved_fortress_coverage` counters remain one for every native predictor seed, including positive predictions.

`store.py` adds a schema-compatible `discovery_tasks` table and covering status index. Two pending tasks per seed commit in the same transaction as seed summaries, candidate records, counters and completed range digest. Discovery evidence remains in the seed summary instead of being duplicated into each task. Original seed summaries and atomic retry digests are unchanged by subsequent recovery evidence. A failed task insertion rolls back the entire coverage transaction.

Recovery APIs:

- `get_discovery_task(index, structure)` and bounded `iter_discovery_tasks(status=None, structure=None, batch_size=256)` expose original observation and separate recovery evidence.
- `claim_discovery_task(worker)` claims one pending lease and increments attempts. `recover_discovery_assignments()` explicitly restores abandoned leases after the recovery owner is known to have stopped. Baseline scanner startup does not steal discovery leases from a separate recovery consumer.
- `complete_discovery_task(index, structure, evidence)` requires a claimed task and explicit actual-generation source/provider/version matching the target, seed/structure identity, exact discovery settings/bounds, full coverage and verification flags, and consistent in-bounds coordinates/absence. Native prediction cannot close recall. Completed evidence is immutable and identical completion retries are idempotent. This validates supplied metadata, not the truthfulness or exhaustiveness of an external provider.
- `backfill_discovery_tasks(after_index=None, batch_size=256)` explicitly visits at most one legacy page, with a returned cursor and idempotent inserts. Missing historic observations are marked `LEGACY_EVIDENCE_UNAVAILABLE`; no coordinates, absence, or full recall are fabricated. Opening an old run does not run an unbounded migration.

Baseline bonus uncertainty now separates sampled prediction intervals from actual generation intervals. Optional actual bonuses remain `[0, configured maximum]`; actual biome bounds use biome uncertainty, or `[0, maximum]` when deferred. Required actual eligibility remains unresolved independently of predictor pending reasons and bonus intervals. Existing scalar score/qualification behavior remains intact; the score label no longer advertises a predictor score as an actual-generation lower bound.

The runner already persists all seed summary fields atomically, so no runner source change was necessary. No discovery recovery executor/CLI scheduling or authoritative exhaustive discovery provider was added. Recovery does not silently insert newly discovered anchors, rewrite original seed evidence, or change candidate qualification or completed seed coverage. Complete Stronghold recall and authoritative absence remain unproven for the native predictor.

Focused synthetic verification covers no-anchor evidence, positive-anchor unresolved recall, atomic insert failure, restart/reclaim attempts, source/settings/bounds rejection, immutable idempotent recovery, legacy bounded migration, and prediction/actual bonus bounds. No native benchmarks or BDS runs were performed.

Known integration follow-up: weight-only rescoring must refresh these new uncertainty fields together with scalar bonuses; root was notified because `reports.py` is outside this task's ownership.
