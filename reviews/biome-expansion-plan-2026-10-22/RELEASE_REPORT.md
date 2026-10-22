# Biome expansion — completed and adopted

The approved biome expansion and section 5a reserve behavior are implemented,
verified and adopted on the idle public backend. Local UI:
http://127.0.0.1:5173/#catalog . Personal backend PID 91321 remains unchanged.
No commit, merge or push was made.

## Released behavior

Personalized Selection supports 56 individual Overworld biomes, four convenient
ANY-member groups and the five existing Nether choices. The existing four-pillar
UI now has compact searchable categories, expandable groups, snapshot-bound
capabilities and predicted XYZ witness details. Alternatives within one row mean
ANY; separate required rows must match around the same anchor. Missing observations
remain unknown. Required/preferred rules, comparison, favorites and paging remain.

All 56 exact Overworld choices passed the approved activation gates. Snowy Beach
uses Y63 only because additional-height controls disagreed. Predicted igloo basement
and treasure bastion remain gated: compatible independent variant controls were
not established. The [stronghold investigation](STRONGHOLD_COVERAGE.md) preserves
the partial-coverage label and current predictor. Predictions do not certify terrain,
landing, safety, exhaustive absence or physical instance counts.

New personal engine runs with Top50 retain 100 distinct candidates throughout
screening and pruning, display 50 primary candidates, and expose an optional reserve
view. Checkpoints, SQLite and caches record both capacities. Historical runs retain
their recorded limits; discarded candidates cannot be reconstructed. The preserved
personal process continues its loaded historical implementation; it was not restarted
or silently upgraded during this release.

Public objectives retain up to 2K distinct worlds total and display K by default.
The contract declares 7,543 objectives, 115,964 primary slots and 231,928 retained
slots. These are capacity bounds, not unique-world counts. The saved cohort has
109,438 actual memberships across 222 worlds. Roles belong to each objective;
generic selection queries the retained union. Shared observations are stored once.
Reclamation protects reserves, pins, in-progress verification and extension artifacts.
Historical reserve completeness remains explicitly false.

Explicit finalist advancement uses `finalization_operator.finalize_objective` and
existing SQLite/CAS receipts. It follows frozen rank order, promotes actual passing
reserves after scoped failures, leaves inconclusive higher candidates pending, and
reuses compatible physical evidence across lists. No automatic BDS campaign or
verification-budget increase was introduced. Candidates remain predicted until
actual evidence certifies their advertised conditions.

## Independent verification

- Full catalog regression: **637 passed in 285.47 seconds**. The subsequent startup
  cleanup/status/metadata focused run passed all eight checks. Earlier missing
  isolated fixtures were restored; the final full run has no failures.
- [Migration audit](FINAL_CATALOG_AUDIT.json): 222 worlds, 54,615 summary rows,
  4,041,510 feature comparisons and 109,438 membership bindings passed. Original
  observations, Realm/product evaluations, historical snapshots, mode-specific
  legacy payloads and old primary prefixes are preserved. Coordinate proof reuse
  requires exact equality of every nonlegacy numeric/source field with the prior
  fully audited block; changed facts cannot bypass the coordinate oracle.
- [Reserve replay/full sort](RESERVE_FULL_SORT_AUDIT.json): all 7,027 existing
  objectives passed across all 222 saved worlds. Frozen per-world scoring is reused;
  exact normalization and whole-cohort sorting are independent of the new ledger
  and bulk merge. Versioned layout IDs are normalized; any embedded rank must first
  equal its authoritative rank. The separate coordinate audit checks all 504 atomic
  biome objectives and requires the 12 gated auxiliary objectives to remain empty.
- [HTTP acceptance](HTTP_VALIDATION.json): all nine mixed queries passed in
  **2.60–4.98 seconds**, below the unchanged 10-second deadline. The 12-row,
  16-alternative stress case passed in **6.15 seconds**. Mixed-height same-anchor
  AND passed with 216 matches and six unresolved worlds. Paging is disjoint.
- All 36 products passed primary/reserve checks; all **72 real responses** passed
  the [frontend decoder](LIVE_PRODUCT_DECODER.json). Actual two-page primary and
  reserve checks passed, and a cursor from the wrong view was rejected.
- A [historical share query and detail](OLD_SHARE_VALIDATION.json) passed against
  the old immutable snapshot. Unsupported V3 choices on that snapshot return an
  explicit capability error. All 36 snapshots remain listed and readable.
- [Ranking parity](QUERY_RANK_PARITY.json): 72 before/after cases over 1,458 rows
  preserve complete responses, including pending results and all feature counts.
  Strict stale-validator fallback, corrupted pages, changed bindings, mutation
  isolation, cache bounds and worker cleanup are covered by actual tests.
- All ten catalog Node suites, network/telemetry checks, 25 new UI checks and the
  production frontend build passed. All 12 integrated UI files still match the
  verified build's hashes. Interactive browser QA remains waived.

## Measured evidence and resource use

Archived replay reused 19,841 exact XYZ points from 29 worlds. Fresh controls on
two existing seeds produced 36/36 exact XYZ matches, including the six mountain
methods on both worlds, in 68.472 seconds of BDS wall time. The pinned build/settings,
CPU/memory bounds and one-server-at-a-time rule were preserved. Portable controls
and member checksums are in `fixtures/bedrock-26.52/biome-expansion/`.

The alternating-order height pilot used 16 saved worlds and took 759.676 seconds.
Median baseline extraction was 23.639 seconds versus 23.960 seconds expanded:
**1.36% increase**, passing the 25% gate. Structures and Realm inputs matched.
Positive and exact nonmember controls do not imply world-wide absence.

The initial migration completed in 3,150.624 seconds but was rejected for a query
latency failure and a legacy grid/spawn collision. Those failures were preserved
and corrected. The user explicitly approved one additional 180-second allocation
following Gemini High review. Final charged migration time was **3,617.6 seconds
of 3,780**, including conservative crash reservations; it was not reset. Aggregate
output was **1,668,140,009 bytes**, below 2 GiB. The cohort contains 710,400 added
public height points. The 4 GiB RSS and all artifact/IPC/query limits were retained.

The synthetic 10,000-record tracker benchmark measured Top50 versus Top100 heap
medians of 0.1015 versus 0.0986 seconds (noise, not a speed claim), SQLite flush
medians of 0.00095 versus 0.00159 seconds, and live traced heap bytes of 25,208 versus
61,872. A lower reserve cutoff can increase native materialization; no production
scan-throughput improvement is claimed.

Serving loads a compact verified metadata index before readiness under the existing
cache allowance. Queries rehash the binding, index and every manifest page on reuse;
no mtime shortcut replaces checksums. Query result/projection caches were cold for
the reported first requests; this is not a cold-filesystem or load SLA claim.
The two adopted query workers initialized in 6.77 seconds total, each retaining its
original startup deadline. Server readiness was observed within 49.03 seconds of
restart, including metadata initialization. Snapshot listing then took 0.55 seconds.

## Adoption and preservation

The [live smoke check](ADOPTED_SMOKE.json) passed after adoption: current query
4.84 seconds, detail 4.67 seconds, expected 216 matches/six unresolved worlds,
56 active exact choices, correct Vite proxy and active public control with
**0/600 seconds consumed, no jobs and no campaigns**.

Serving root:
`/Users/lucasraicu/.local/share/antigravity-worker-mcp/biome-expansion-approved-20261022/catalog-corrected`

Snapshot: `9637bc21753fa249775f0b11e84ec7a9a92d3872d7982f8e3dfd9a2be4859421`

Policy: `19d814fc5ca3ca9d5b131f14f3c50abd3e912da11bcfef1ed8709ec012b7c75f`

Public PID 18349 serves port 3001; Vite PID 17880 serves 5173. The owned test preview
was closed. Personal PID 91321, its runtime identity and run are unchanged.
[All 199 protected personal/checkpoint/native files](PERSONAL_PRESERVATION.json),
[57 native source files and legacy function/Prototype ASTs](SOURCE_PRESERVATION.json),
and all 11 legacy JSON contracts match baseline. Public scoring remains 845/265/140;
borders and the fixed Nether window are unchanged. The old public root remains
available for rollback and historical links. No new large search was launched.

Gemini High contributed core, retention, UI, the independent audit and scoped
reviews. Codex read every patch and changed file, corrected demonstrated defects,
resolved disagreements against source/tests and independently validated integration.
Failed, denied, timed-out and context-limited submissions remain recorded in
[the reconciliation](IMPLEMENTATION_RECONCILIATION.md) and `workers/`. No account
switch, quota bypass or permission bypass occurred. No required release work remains.
