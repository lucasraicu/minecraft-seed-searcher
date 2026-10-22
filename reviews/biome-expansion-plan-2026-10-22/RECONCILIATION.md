# Independent plan critiques — Codex reconciliation

Date: 2026-10-22. Plan only; no implementation or searches.

Both Gemini tasks used gemini-3.8-flash-high, explicit effort high, 900s timeout,
120 CPU seconds, 2GiB, read-only isolated dirty snapshots, no permitted commands,
no owned paths. Both succeeded with exit0, denied_actions[], substantive untruncated
responses, no file changes and no tests. Actual task records are saved beside this
file. Combined reported usage: 39,592 tokens; remaining account quota is unknown.

## Accepted or clarified

- Overlapping atomic/group IDs need a one-to-many mapping or atomic summaries
  with group unions. The actual current scalar inversion would drop witnesses.
- Y63-only summarization must not discard eligible multi-height samples. Bind
  profiles, dimensions, original observation and extension evidence throughout.
- Fixed-height sparse detections are coordinate witnesses, not surface terrain,
  true nearest-boundary measurements, absence proofs or exhaustive discovery.
- An extra 32,000 evaluations is too aggressive for a cost-sensitive first trial.
  Reduced proposed extra survey to stride256/five planes (8,000 points before
  reuse) and prioritize existing Realm -48/0/160 samples. Cost gate stays <=25%
  median full public-world wall increase and <=120s/world. Failure leaves features
  gated, not implicitly authorizing higher cost.
- Keep v1/v2 schema/readers/history; explicitly version v3 registry, summaries and
  request handling. Reuse current SQLite/CAS/queue instead of a parallel framework.
- Added sample evidence must not silently change frozen Realm scoring inputs.
  Proposed CAS extension binds raw original observation and additional point data;
  source IDs, profile IDs and eligibility are checked in summaries/cursors/projections.
- Freeze Top20 capacities explicitly. Full added membership capacity is 10,320
  across 516 objectives, total115,964 slots/7,543 objectives. Fixed Nether windows
  have only one list per mode, not three copies for Overworld border choices.
- Existing 16MiB artifact, 1MiB request, 4MiB reply and 10s query caps must be checked
  with expanded features; preserve12rows and cap within-row alternatives at16.
- Before fresh BDS, tabulate compatible archived observations and remaining missing
  per-feature controls. Two independent seed witnesses must be actual matches, not
  inferred from names. Up to8 fresh/control worlds is a budget, not a guarantee all
  desired features pass. Failed/insufficient methods remain unavailable.

## Rejected or corrected

- Reviewer A's inclusive lattice count is wrong for our half-open bounds. Width
  10240/stride64 yields160*160=25,600 baseline points, not25,921. Initial stride128
  five-plane proposal was32,000, not32,805; revised stride256 is8,000 before reuse.
- A25% whole-pipeline wall gate is not mathematically contradicted by a larger
  percentage of point calls. Structure/Realm work and reusable observations matter.
  This remains an empirical gate, not a promised result.
- Twenty positive coordinate checks do not require twenty worlds. One world may
  contain many biome types. Eight worlds are not mathematically insufficient;
  neither are they guaranteed sufficient. Keep the budget and conditional activation.
- Reviewer B suggested uncomputed/gated witnesses become 'deterministically absent'.
  Rejected: missing/partial data stays UNKNOWN; globally unsupported/gated selections
  get capability errors. OR with a valid positive can match; AND with unresolved
  requirements stays unresolved. No potentially good seed is deleted as absent.
- Empty TopK lists in222worlds are not a defect, and Top20 is not a population
  prevalence claim. Do not populate lists with fabricated or nonqualifying worlds.
- Avoid declaring all non-mountain choices '2D biomes': every witness still has XYZ.
- A new catalog/v3 Python package is not required by versioned contract files.
  Use a small version-specific adapter where necessary, without duplicating stores.

No disagreement authorizes a native correction, broader game run or implementation.
User review/approval of the final plan remains required by AGENTS.md.

## Focused final delta review

Task5d564be6a21b used the same High model, 600s/90CPU/2GiB, no commands or writes,
exit0/denied[]/substantive output. It found no new architectural blocker in the
extension binding, stride256 profile and fixed query bounds. Reported20,023tokens;
all three tasks total59,615tokens, no exposed remaining-quota estimate.

Accepted nullable extension_id for worlds using only compatible saved evidence;
explicitly require non-null extension existence/checksum/base/profile/provider
binding and GC reachability. Rejected silently pruning gated members from a named
group: that changes its meaning. Keep original declared members and UNKNOWN where
no positive witness establishes the OR. Snowy Slopes remains a core member, not
one of the six newly gated mountain choices. A plan review cannot guarantee the
10s deadline from term counts; actual end-to-end cases remain required. No extra
review/model call is needed for these straightforward clarifications.

## Whole-sweep 2x reserve amendment

User requested2x reserve across personal search and public catalog ("Lmk"). Added
section5a to the proposal, not production code. High narrow review11d530d30c6c
succeeded with gemini-3.8-flash-high/efforthigh, exit0/denied[], no edits/tests,
21,413reported tokens. All four plan-related tasks total81,028reported tokens.
No quota/auth error. Actual substantive JSON saved as GEMINI_RESERVE_REVIEW.json.

Codex verified against actual native_batch.py: tracker capacity also determines
cutoff passed to prototype.sweep, and capacity changes are rejected on resume.
Top100 must therefore exist during screening; a UI-only second50 cannot work.
Accepted reuse of one2K tracker/list, primary[:K]/reserve[K:2K], policy-derived
new-ledger/manifest guards, per-objective roles, union reachability and checkpoint
identity. The reviewer found no new blocker. Correct its linked snapshot path
(which omits src/): actual code is src/seed_search/realm/native_batch.py; this was
a supplied-excerpt review, not a command execution or independent source search.

Top50 retains100total, Top20 retains40total. Full primary115,964 slots =>231,928
retained slots across the same7,543objectives. This does not imply2x unique worlds,
BDS workload or scan runtime. More materialization/storage and weaker pruning are
real cost risks to measure. Old data can yield only historically incomplete
reserves where earlier pruning discarded inputs. No retroactive rescan authorized.
No overall completion notification while the amended implementation awaits approval.
