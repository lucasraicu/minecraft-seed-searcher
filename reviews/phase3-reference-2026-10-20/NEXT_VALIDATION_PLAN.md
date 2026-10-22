# Larger CPU ingestion, retention and recovery validation — proposed execution

2026-10-20. User requested inclusion of this stage after the reference slice.
Concrete limits below are proposed for review under AGENTS.md. No larger seed run
has started. This stage does not include the public website, GPUs, custom storage,
billing, live deployment or a10000-world campaign.

## Objective and prerequisites

Move from the implemented two-world reference to a bounded, varied100-world
developer corpus; exercise durable ingestion/recovery and exact fixed-objective
retention; quantify loss for supported requests against an unpruned reference.

The two-seed probe completed all23 features and486 layouts on one CPU thread:
4.78s extraction,6.44s total including summaries and publication. This is a smoke
measurement on two natural seeds, not a calibrated diverse-world throughput model.
Snapshot restore, query oracle and full regression are required before expansion.

## Scope and architecture

- Preserve scripts/catalog_reference.py's original two-seed cap and original run.
  Add a separate bounded validation CLI and ingestion coordinator over the same
  models, extractor, summaries and artifact/SQLite store; no personal scan hook.
- Predeclare100 distinct signed64 seeds using seed_from_index(i,0xCA7A11), i0..99,
  before feature evaluation. Do not choose personal survivors or hide failures.
- Run serially at first, one native CPU thread, supervised subprocesses. Total
  extraction wall cap15minutes, full validation job wall cap30minutes, aggregate
  RSS4GiB and new output2GiB. Enforce before and during writes; report partials
  on caps. Smaller staged preflight10 worlds then remaining90 under same budget.
- Persist schema/source/build/settings/cohort identities, next index, per-world
  feature progress, receipts and resource reservations. Restart uses unchanged
  controls, no duplicate committed worlds and no silent additional budget. Safe
  cancellation and explicit partial/failed records are part of success criteria.
- Batch immutable observation artifacts and summary publication. Keep all complete
  reference observations for comparison; retention is a derived selection view,
  not physical deletion. Never modify the personal database or live service.

## Retention implementation

Implement the existing PUBLIC_CATALOG_SYSTEM_SPEC.md section7 objective families,
not Argon's35-bit mask heuristic:14 structures x4 scopes x3 sides x2 modes for
counts; structure proximity;9 biome proximities;9 biomes x4 landmarks;16 profiles;
256 exact diversity cells x4 profiles; stable-hash reference sample and explicit
pins. Names, normalizers, capacities, stable salt and all comparison tuples come
from docs/catalog/v1/public_policy.json. Missing details must be resolved against
the consolidated specification before code; do not invent admission thresholds.

Each objective evaluates eligible layouts of the correct border/mode, picks each
world's best qualifying anchor, deduplicates worlds BEFORE K and uses one total
rank for serial/partitioned/reversed merges. Public usefulness is independent of
personal floors. Feature coverage must suffice for the objective; a failed feature
does not discard unrelated valid features. No player query adds unbounded buckets.

Production-default capacities plus a10000-world reference reservoir would retain
all100 reference worlds, so that alone CANNOT validate selective retention.
Test versioned reduced-cap policies (e.g. K1/K2 specialist/profile lists, small
reference reservoir) and adversarial synthetic worlds that oversubscribe each
objective. Report the actual retained count; if the union still retains every
world, label that experiment non-discriminating rather than claiming recall.
Later larger-than-cap reference work requires a separately sized campaign.

## Query evaluation and recovery evidence

Freeze at least200 held-out request cases before examining retained results,
covering Required/Preferred, counts, biome alternatives, eight category presets,
all three sizes, both anchor modes, rare combinations and broad/low-selectivity
queries. Do not tune retention on that same request set. Evaluate unpruned versus
retained snapshots with the same query semantics. Record nonempty preservation
only where the reference is nonempty, unique-world top10 recall with explicit
denominators, normalized score regret and failures per request family. Existing
95%/90% goals are experiment targets, not guarantees over Minecraft's seed space.

Expand fault tests: terminate an owned ingestion subprocess at feature progress
and publication boundaries, resume with matching controls, verify deterministic
publication and no double accounting. Test artifact truncation/checksum mismatch,
incompatible revisions, failed durable writes, missing bundle, snapshot restore
from metadata+artifacts, and concurrent readers seeing complete generations only.
Never kill the existing server or another worker's process. Use synthetic injected
failures for most boundary tests; real seed records are reused, not regenerated
for each crash case. A Python exception test alone is not proof of process-death
durability; distinguish both in the report.

Measure per-feature extraction wall/CPU and tail, summaries, packed/artifact bytes,
metadata growth, record reconstruction, query costs and retained-world usefulness.
Record actual hardware/thread/source identity and background contention. No
submillisecond gate or GPU speedup projection. Preserve unknown/partial status;
query agreement is predictor/observation agreement, not actual Bedrock truth.

## Work order, ownership and acceptance

1. Codex freezes cohort/budget, ingestion receipts, ranking APIs and experiment
   descriptors, based on the independently critiqued plan and existing contracts.
2. High Gemini A owns bounded ingestion/replay tests; High Gemini B owns retention
   objectives and deterministic merge tests. Ownership does not overlap.
3. Codex owns independent retention oracle, held-out evaluation, crash supervision,
   integration and report. Use fewer workers while interfaces are coupled.
4. Synthetic tests and small process-death tests first, then the10+90 world run
   within one fixed budget. Stop/report if costs or coverage violate limits.

Acceptance: all requested geometry/evidence semantics preserved;100 attempted
world receipts accounted for or explicit budget exhaustion; complete features and
failed features distinguished; no cross-world/anchor joins; exact retention versus
independent serial oracle; partition merge parity; reproducible query metrics;
successful crash/replay and backup restore; relevant project tests pass; original
service/source/native binaries preserved. Do not declare all100 worlds complete
merely because100 seeds were attempted. No production features activated.

Engineering estimate: several focused working days to1–2 weeks, depending on
recovery findings and objective ambiguity. The budgeted100-world compute run is
not itself a week-long job. Use its evidence to estimate a later10000-world study.

## Independent High critique and resolution

Review617ed6a13c38 succeeded with gemini-3.8-flash-high --effort high, exit0,
substantive response, no denied actions/edits. Earlier8c467d607100 attempted a
denied RunCommand and failed; no result accepted or permissions broadened. A
tool-free replacement used embedded context only. An oversized objective was
also rejected at submission validation; it did not launch a model process.

Accepted: explicit empty-reference denominators, separate reduced-cap experiments,
frozen total rank tuples, process-death injection and checks for leaked workers.
Codex qualifications/corrections:
- Reduced-cap experiments on the natural100-world corpus can produce useful
  local metrics IF they actually prune worlds. Synthetic evidence is essential
  but need not be the exclusive source of metrics; neither proves production
  capacity recall. Report each corpus and retained fraction separately.
- Preserve each existing objective's specified rank; do not substitute a generic
  objective_score/anchor_distance rank. Canonical seed ties use UNSIGNED bit-pattern
  order, then declared center/layout keys, not implicitly signed seed ordering.
- No automatic startup directory sweep. It could delete another live writer's
  staging files or referenced/pinned artifacts. Track orphan generations and
  collect only with exclusive ownership and a validated reachability manifest;
  quarantine is acceptable until safety is proven. SQLite recovers its own WAL;
  never manually delete WAL/shm or reset a database to clear contention.
- Suggested150s/10world and1GiB gates are not measurements or accepted changes
  to limits. Use the stated hard caps, account tail costs, and stop before the
  remaining90 if conservative measured cost predicts budget exhaustion.
- Existing functional query costs include raw observation validation (~0.17–0.19s
  for2 worlds under shared background load). The next stage must measure this
  separately from summary filtering. Build a version-bound immutable verified
  snapshot read view to avoid revalidating all raw samples for every query while
  preserving identity checks. Do not drop provenance/validation to hit a target.
- A SIGKILL test is an actual owned-process termination under test, not a Python
  exception simulation and not hardware power-loss certification. Saved metadata
  and artifacts must restore independently of the source run's temporary files.

The High review estimates4–7 working days plus recovery uncertainty; treat that
as planning judgment, not a tested delivery date. No unresolved requirement
justifies changing personal search, public tier parity or evidence semantics.
