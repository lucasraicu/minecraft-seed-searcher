# Codex review of the parallel Gemini outputs

Reviewed 2026-10-14. These reports describe a changing working tree; their line numbers and statements about missing implementation are snapshots. They are review input, not certificates or executable acceptance results.

| Output | Disposition after checking source |
| --- | --- |
| Geometry oracle / half-open bounds | Accepted: 1664 blocks means `[C-832,C+832)`, not 1665 inclusive blocks. Overworld start events are `p-831,p+833`; projected Nether events are `8(p-416)+1,8(p+416)+1`. |
| Geometry constrained snapping | Accepted: select the nearest valid multiple of 16 on each axis, falling back to 8 on that axis. Never force a center outside the cell. A cell with no valid grid point is unusable. |
| BDS fabrication inventory | Confirmed against the old handler. Removed synthetic metrics and DB promotion, and removed sample candidates from initial website state. An owned subprocess now delegates to the existing real `verify-biomes` command. |
| BDS evidence scope | Accepted: the current automated provider can observe bounded surface points/blocks. It does not establish a whole Realm, portal room, generated structure inventory, loot or a player's first join. Old stub-shaped `VERIFIED` data is not trusted by the website. |
| Scoring / ranking drift | Confirmed in the earlier snapshot; fixed targets, bonuses, hub score, strict categories, native/Python parity and the four-level SQLite order. Historical policies retain their historical formulas. |
| Ambiguous third / fourth bonuses | User resolved explicitly: **one-time +20 at the third structure, one-time +25 at the fourth Ancient City**. No additional award for later instances. |
| Claimed absence of an Igloo basement predictor | Incorrect: the pinned vendor `getVariant()` has an Igloo case and a basement PRNG roll using its population RNG. The bridge now exposes that predictor. This remains model evidence, not BDS-observed basement or loot. |
| Mega-cave bonus | Not accepted from a biome ID alone: climate noise does not establish an open cavern entrance. No invented +4 entry bonus is awarded. |
| Distributed throughput / cache efficiency / latency percentages | Unverified. The reports provide no measurements of this completed revision. Estimates such as 75–90k cluster rate or 95% cache hits are not adopted. |
| Claimed joint probability is statistically established | Not accepted: dividing 36B by an assumed joint rarity is arithmetic, not calibration of the rarity or a guarantee of candidates. |
| Distributed runbook certification / noise shortcut | Not accepted: the current implementation keeps exact biome lookup; heuristic climate thresholds do not prove zero false rejects. Runbook language does not establish certification. |
| Shard allocator storage estimates | Do not use as the runtime disk gate. Runtime `resources.disk_policy` uses 32 projected bytes/input for compact retention and 65,536 for full retention, with reserve/limit checks. At 36B inputs the full estimate is 2.36 PB decimal; compact is 1.152 TB decimal before overhead. |
| Shard allocator input validation | Review artifact only: `generate_shards(..., shard_size=0)` would loop indefinitely; negative and overflowing inputs also need validation. Use verified exact, disjoint intervals and runtime admission checks. |
| Benchmark protocol | Adopt bounded trials and counterbalanced held-out validation, but measure the actual executable and report kernel and durable rates separately. Do not run competing benchmark jobs. |

Current executable regression evidence and final adoption measurements will be recorded in `LATEST_PUSH_REVIEW.md` and the dynamic benchmark report. External reports' `code_behavior_observed` fields are not accepted as executed tests without reproducing them.

## Reproduced scoring-fixture issue

The generated JSON contains 104 cases. All 55 passing cases with explicit counts, numeric `smart_score` and no hub items disagree when run through the resolved score formula (`reviews/scoring_expectation_recheck.json`). For example, its baseline counts include 9 Villages, 8 Trial Chambers, 4 Ancient Cities and 3 of each temple: those already earn 25+10+25+20+20=100 points, while the fixture expects zero. The supplied score fixtures therefore cannot be adopted as acceptance tests unchanged. Fatal/rejected cases are excluded from this comparison because they produce no ranked candidate.

## Follow-up worker review

Gemini's follow-up corrected the half-open documentation, fixture totals, milestone language, storage model and allocator input validation. Codex found two remaining problems and corrected them before integration:

- The generated launch scripts used scan flags `--policy` and `--run-key`, which the real scan parser does not support. Scripts now write a validated per-shard YAML and use `--config`; shell arguments are quoted, and excessive shard counts are bounded.
- The revised blueprint still implied the existing headless surface provider would certify portal rooms, loot and initial-player spawn. Those claims are removed; the limitations are explicit. A biome witness alone does not earn the physical mega-cave entrance bonus.

The 55-mismatch JSON records the **initial** scoring-fixture snapshot, before Gemini's follow-up corrected it. Final checker execution and comparison against production scoring are recorded separately after benchmarking.

## Executed follow-up checks

- Independent Gemini geometry oracle: exhaustive internal checks plus 38/38 supplied geometry cases passed.
- Independent Gemini scoring checker: 104/104 cases passed. Production policy independently matches all 96 explicit qualification fixtures and all 78 passing numeric score fixtures, including the capped hub contribution.
- Shard allocator suite: 92 tests passed. A supplied test incorrectly rejected the documented `None` default-rate sentinel; corrected the test while preserving strict count/batch/rate validation.
- Final disjoint held-out adoption: all-input persisted decision receipts and candidate digests match in five counterbalanced pairs across 500,000 distinct seeds. See the benchmark report for performance and cohort limits.

- Generated shard commands were exercised through YAML validation and the real CLI `--dry-run`: exact range accepted and zero inputs executed.
