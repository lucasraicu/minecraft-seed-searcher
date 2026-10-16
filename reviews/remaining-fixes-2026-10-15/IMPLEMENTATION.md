# Remaining audit findings — implementation and verification

Date: 2026-10-15. Scope: R1–R7 in [the follow-up review](../final-followup-233fad7/REPORT.md), applied on top of the user's existing working-tree changes.

Status: **R1–R7 fixed and verified on the current working tree.** The final full suite passes; source hashes are retained in `manifest.json`.

| Finding | Delivered change | Regression evidence |
|---|---|---|
| R1: historical campaign defaults | Campaigns default to `config/realm.yaml`; the deficit budget is resolved and validated from the selected profile unless overridden. Explicit historical v1 still resolves budget 2. | Generated command resolves v2, empty terrain variants, budget 3; a real CLI dry run reports 17 planned inputs and zero executed inputs. Historical and explicit overrides are checked. A real two-input native run saves the explicit budget in its policy/identity and resumes with that same budget. |
| R2: inconsistent rescoring | Scenic pairing is recomputed from the complete retained Y=63 selected-window lattice. Village spread and treasure are recomputed from retained coordinates/variants. Totals, flags, category names, hub/scenic/River/triple witnesses update together. Missing required samples/variants produce specific errors. | Stale flags cannot change the recomputed result. Positive scenic/spread/treasure evidence yields 20/15/15 and matching serialized fields. Missing surface/variant evidence is rejected. |
| R3: capped result access | The API reads bounded SQLite pages in one read snapshot, with database totals and canonical ordering. Default limit 100; allowed 1–250; validated offsets. Dashboard Previous/Next controls request pages directly and retain the selected page during telemetry polling. Default filters include negative scores. | HTTP test retrieves the final candidate beyond 5,000 from a 5,101-row database; validates page bounds and verifies the manager does not materialize that full result set. Actual UI handlers advance pages, and negative candidates remain visible. |
| R4: merge ranking | Merge summaries use revision-aware ordering through `order_for`. | A 100-point eligible v2 result with one deficit ranks above a 50-point result with none. Existing historical merge tests pass. |
| R5: stale checkpoint readers | Public `get_state` reads SQLite for current committed state; private single-writer counter helpers retain their fast cache. Rollback invalidation remains. | A separate long-lived reader sees the writer's new completed-input and counter values. Existing atomicity, retry, and rollback tests remain enabled. |
| R6: missing player information | New v2 records retain optional inspection states. API/detail views expose the predictive community-spawn suggestion separately from actual initial spawn. End access, portal links, and snow/ice resources default to unverified; supplied inspection provenance is preserved. CSV and readable exports include the new information. | Record serialization keeps suggested and actual spawn distinct, defaults inspection states honestly, and preserves supplied provenance. Actual detail-component rendering is checked. |
| R7: contradictory policy documents | Blueprint matrix, hub rules, predictor terminology, caps, and complete ranking key match the agreed v2 schedule. README documents current campaign, pagination, rescore, and evidence behavior. Historical v1 remains explicitly labeled. | Reconciled against the authoritative v2 scorer and historical configuration. Acceptance status links to this evidence instead of a blanket implementation claim. |

## Verification

- Focused existing shard/merge/store/web checks: **40 passed** ([log](focused-existing.log)).
- Added Python regressions and actual TypeScript component tests: **11 pytest checks passed**, including ten new Python cases and the existing Node test wrapper ([log](focused-regressions.log)). The wrapper also exercises the three new UI behavior cases.
- Full Python suite: **1,114 passed in 309.79 seconds** ([log](pytest.log)).
- Production web build: passed ([log](web-build.log)).
- Web lint: passed without warnings ([log](web-lint.log)).
- Whitespace verification: `git diff --check` passed.

No native C scoring or climate logic was changed for this remediation. The changes reuse the existing pipeline, SQLite writer, leaderboard indices, and retained data; no automatic terrain/BDS work is added.

## Existing records and deployment

Historical review reports remain snapshots of their reviewed versions. This document records closure of their remaining findings.

Rescoring repairs the score and explanation of a retained window. It cannot recover another center discarded by an earlier selection bug. Affected seeds need re-evaluation if the correct original winning center is required. Older v2 records without complete surface/variant evidence are explicitly rejected by rescoring rather than assigned fabricated zero bonuses.

Retain normal computation-identity checks when choosing fresh runs or resuming campaigns. This work changes evaluator/report source identity; it does not rewrite existing campaign databases or silently replace their saved identities.
