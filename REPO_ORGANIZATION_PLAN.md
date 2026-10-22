# Repository organization and preservation plan

Status: COMPLETED APPROVED SAFE ORGANIZATION, 2026-10-22. Both exact four-document
batches were approved and applied; eight files moved, zero payloads deleted.
Four navigation indexes cover the retained source/test/evidence paths. Root Markdown
files decreased from 22 to 14. Riskier source/test refactors are optional separate
projects, not unfinished cleanup. The original Gemini proposal is preserved in
`reviews/variant-controls-and-organization-2026-10-22/ORIGINAL_REPO_ORGANIZATION_PLAN.md`.

The companion variant release also passed: igloo-basement and treasure-bastion
filters enabled, 222 worlds / 109,918 memberships, all historical data preserved.
See [completed release](reviews/variant-controls-and-organization-2026-10-22/RELEASE_REPORT.md).
The dated baseline below records the pre-organization state; it is not current
runtime configuration. Exact move/rollback manifests accompany that release.

## Publication refresh — 2026-10-22

The user subsequently requested cleanup and a GitHub push. The safe physical
organization above remains complete. This refresh updates navigation, adds an
independent Claude/Gemini audit prompt, removes duplicate ignore entries without
changing ignore behavior, and publishes the inspected source/tests/fixtures/review
receipts. No additional physical moves, payload deletions or source refactor are
included. Source-sensitive paths and historical evidence retain their exact bytes.
See [publication scope and verification](reviews/repository-publication-2026-10-22/REPORT.md).
Private catalogs, live runs, environments and binaries stay local; repository
publication is not live adoption, GPU implementation or a database migration.

## 1. Current state and objective

Organize navigation and storage without losing evidence, dirty work, reproducibility
or historical compatibility. A clean Git status is not a prerequisite and must not
be manufactured with a reset, stash, clean, blanket ignore rule or unsolicited commit.

Inventory at this review's start:

| Location/state | Observed count |
|---|---:|
| Root Markdown files | 22 |
| Direct files in scripts/ | 169 |
| Direct files in tests/ | 140 |
| Catalog Python test modules | 80 |
| Review directories before this task | 43 |
| Tracked files | 1,225 |
| Dirty/untracked file entries (`git status --porcelain -uall`) | 878 |

These are dated observations, not permanent quotas. They include inherited work.
The new review directory increases the review count after inventory. The baseline
contains hashes for proposed move classes and the original expanded Git status.

The biome expansion is COMPLETED AND ADOPTED, not an active unfinished migration:
56 exact Overworld choices, four groups, five Nether choices, expandable UI and
per-objective 2K reserves. All 222 saved worlds have 109,438 memberships. The contract
permits 7,543 objectives / 231,928 retained slots, not that many unique worlds.
637 catalog tests, 72 actual product-response decoder checks, full coordinate/history
and reserve-sort audits passed. See the release report before selecting archival
material; these files are active release evidence.

Live baseline: personal PID91321/3000, public PID18349/3001, Vite17880/5173.
Public snapshot `9637bc21753fa249775f0b11e84ec7a9a92d3872d7982f8e3dfd9a2be4859421`;
policy `19d814fc5ca3ca9d5b131f14f3c50abd3e912da11bcfef1ed8709ec012b7c75f`.
The public root is outside the repository under the persistent worker data directory.
Its 3,617.6-second migration used an explicitly approved 3,780-second allocation;
that finished allocation is not available for cleanup or another migration.

## 2. What must stay intact

- Preserve every tracked, untracked and relevant ignored file in a planned move.
  Dirty/untracked does not mean disposable. Preserve deletions and file modes too.
- Keep `src/seed_search/`, `native/`, `vendor/`, their source fingerprints and both
  native binaries unchanged. Preserve personal scoring, database/checkpoints,
  run identities and historical capacity limits. Do not restart the personal server.
- Keep `docs/catalog/v1/`, `v2/`, `v3/` contracts at their paths and bytes. Registry,
  sampling and retention identities are hash-bound. Do not tidy JSON formatting.
- Preserve `fixtures/`, activation matrices, raw controls, SHA manifests, audit
  scripts/results, review responses, denials, timing failures and reconciliations.
  Unsuccessful evidence is still evidence. Age alone never makes it disposable.
- Preserve the live catalog, all old snapshots/pins/verification receipts, external
  policy roots, isolated baselines and recovery records. Do not move a serving root,
  duplicate it into the repository, or invoke catalog reclamation for housekeeping.
- Leave `.git/`, dependency environments, `runs/`, live logs, SQLite/WAL/SHM files,
  observer worlds and active build/profiling outputs alone unless separately scoped.
  A filename such as `default.profraw` does not establish that its writer is idle.
- No automatic branch switch, commit, merge or push. A branch does not save dirty
  or untracked bytes; `git switch main` is not a rollback of file reorganization.

## 3. Concrete dependency hazards

The old plan's broad script/test moves are not mechanically safe:

- `scripts/build_spawn_estimator.py` and migration CLIs derive the root using
  `Path(__file__).resolve().parents[1]`; another directory level changes that root.
- `scripts/build_count_pilot.py:119` includes its own current path in fingerprint
  inputs. A forwarding wrapper does not preserve that source/build identity.
- Migration/reindex scripts import `scripts.reanchor_catalog`; recovery tests import
  `scripts.reindex_catalog_biomes`. Existing CLI/module invocation forms must work.
- Catalog tests import sibling helpers such as `test_automation_query` and
  `test_expansion_storage`. Splitting tests can break fixture/import discovery.
- CJS tests resolve `../web-ui` from `__dirname`. Moving them beneath `tests/ui/`
  requires explicit path fixes, dependency resolution and actual rendering checks.
- Reports, portable archives, test fixtures and recovery instructions contain
  historical paths. A rewritten report can invalidate a saved hash. Do not rewrite
  frozen evidence to make a link checker green. Runtime evidence also rejects some
  symlink paths, so symlinks are not a general compatibility strategy.
- `pyproject.toml` already has `testpaths=["tests"]`; adding the same setting does
  not solve sibling imports, path constants or duplicate pytest collection.

Before each move, record incoming references, direct execution/import forms,
`__file__` assumptions, hashes, fixtures and the required old-path compatibility.
Classify each file as movable, requires adapter/refactor, or fixed historical path.

## 4. Execution order and ownership

Codex owns inventories, move manifests, preservation, conflict resolution, review,
integration and final acceptance. Gemini High receives isolated snapshots including
relevant dirty files, nonoverlapping writable ownership and exact permitted commands.
At most four workers; no recursive delegation, automatic integration or push.

The variant-validation track may run alongside organization planning and navigation
indexes. Physical moves of scripts/tests/reviews wait until variant implementation
and its writable ownership are idle. A race-free ownership boundary is more useful
than keeping every worker busy.

### Phase A — baseline and navigation (small)

Completed navigation slice: `docs/REPOSITORY_MAP.md`, `scripts/README.md`,
`tests/README.md` and `reviews/README.md`. Verified 451 relative links with zero
missing targets; no physical moves or deletions. The original plan, inventory and
verification are preserved in `reviews/variant-controls-and-organization-2026-10-22/`.
See that directory's `REVIEW_RECONCILIATION.md` for the independent High critique
and Codex's disposition. Later phases remain approval-gated.

1. Capture fresh Git state and active processes; compare with the inventory baseline.
2. Create a recoverable SHA-256 archive of exactly the files proposed for a batch,
   including untracked content and modes, outside the working tree. Verify extraction
   into a temporary directory. Do not back up entire live data/dependency roots.
3. Add concise `docs/REPOSITORY_MAP.md`, `scripts/README.md`, `tests/README.md` and
   `reviews/README.md` indexes, pointing to existing canonical files and release
   evidence. Classify script/test groups without moving them yet.
4. Record decisions and unresolved dependencies. Indexes do not pretend to complete
   physical decluttering; they make subsequent batches reviewable.

### Phase B — root documentation batches (small to medium)

First physical batch approved and executed: catalog architecture/interface spec and
DIAGRAMS moved to `docs/specs/`, the old1664 blueprint to `docs/blueprints/archive/`,
and AUDIT_CONTEXT to `docs/audits/`. All four preserve their original SHA-256/mode;
no deletions. Exact backup, inverse map and approval are recorded in
`reviews/variant-controls-and-organization-2026-10-22/ORGANIZATION_BATCH1_RESULT.json`.
The table below records original source paths and candidate destinations; it does
not imply that remaining batches have approval.

Second batch approved and executed: platform specification and dual-harvest
architecture moved to `docs/specs/`, player policy to `docs/catalog/`, and the
catalog master proposal to `docs/catalog/proposals/`. Only32 relative links changed
across the four moved documents and four active inbound-link documents; prose
is preserved. The verified originals and inverse map are recorded in
`reviews/variant-controls-and-organization-2026-10-22/ORGANIZATION_BATCH2_RESULT.json`.
No historical report or JSON contract was edited. Eight documents total moved;
remaining root documents keep their canonical paths for the dependencies below.

Aim for a compact root with README, AGENTS, CODEX_HANDOFF, active seed blueprint,
server setup guide and this plan. Six entries is a navigation goal, not a rule that
justifies breaking a stable or hash-bound path.

Preserve basenames while moving; do not rename and relocate in the same batch.
These are candidate destinations, conditional on the dependency map:

| Source | Candidate directory |
|---|---|
| MASTER_PLATFORM_SPECIFICATION.md | docs/specs/ |
| CATALOG_WEB_ARCHITECTURE_AND_INTERFACE_SPEC.md | docs/specs/ |
| DUAL_HARVEST_GPU_CATALOG_ARCHITECTURE.md | docs/specs/ |
| DIAGRAMS.md | docs/specs/ |
| PUBLIC_CATALOG_SYSTEM_SPEC.md | docs/catalog/ |
| PUBLIC_CATALOG_PLAYER_POLICY.md | docs/catalog/ |
| PUBLIC_CATALOG_AUTOMATION_PLAN.md | docs/catalog/ |
| PUBLIC_CATALOG_IMPLEMENTATION_PLAN.md | docs/catalog/ |
| PUBLIC_CATALOG_BIOME_EXPANSION_PLAN.md | docs/catalog/ |
| Public_Catalog_Master_Plan.md | docs/catalog/proposals/ |
| IMPLEMENTATION_PLAN.md | docs/roadmaps/ |
| MASTER_SEED_BLUEPRINT_1664_V2.md | docs/blueprints/archive/ |
| CENTER_WEIGHT_RESEARCH.md | docs/research/ |
| AUDIT_CONTEXT.md | docs/audits/ |
| AUDIT_CRITICAL_CODE.md | docs/audits/ |
| AUDIT_SOURCE_BUNDLE.md | docs/audits/ |

Update active relative links and internal links in moved, non-frozen documents.
Keep a small old-path redirect document only where external consumers need it and
where its bytes are not protected. Otherwise leave the file in place and index it.
Never overwrite a destination collision. Record deferred files and their reasons.

### Phase C — script taxonomy (medium; dependency-gated)

Suggested categories: catalog, bds, probes, generalization, calibration, maintenance
and historical tools. These are index categories before they become directories.
Start only with proven independent tools. Keep native build/fingerprint inputs and
active recovery CLIs fixed until their compatibility is demonstrated.

For each physical batch, preserve old direct CLI/module imports using a reviewed
adapter where valid; update root discovery, imports, JS/C source adjacency and
command recipes. A wrapper is insufficient for fingerprint-sensitive builders.
No native rebuild or historical run-identity change is authorized by cleanup.

### Phase D — test taxonomy (medium; separate from script moves)

Consider unit, integration, catalog, bds and ui after a fixture/import audit. Prefer
shared fixtures in explicit support modules/conftest where justified; do not create
ambiguous duplicate module names or shim files that collect the same tests twice.
Verify old supported commands, collection counts and actual tests. Keep tests in
place if relocation has no clear maintenance benefit.

### Phase E — historical reviews and artifacts (optional, evidence-gated)

Create date/topic indexes first. Keep the completed biome release and its linked
control/audit chain easy to find. Physically archive a review only after every
reference and checksum relationship is mapped and the archive is proven readable.
No blanket “all Oct 15–20 folders” rule. Never discard failed controls or logs.

No deletion is included in the initial execution. `default.profraw` may be moved
into a checksummed quarantine only after confirming no active writer/reference.
Add narrow ignore rules only for demonstrated generated outputs; do not hide
valuable untracked evidence. Any later deletion needs its own concrete list and
explicit authorization. Do not add blanket ignores for `runs/`, reviews or fixtures.

## 5. Verification and rollback

Use a reviewed file-level move manifest: original/destination path, type/mode,
pre/post SHA, reference updates, classification and inverse operation. Verify that
all moved payloads remain recoverable and no unrelated dirty file was changed.
If another process edits an owned path, stop that batch and reconcile the drift.

Use an isolated source snapshot/worktree containing relevant dirty changes, with
explicit dependency preparation. Exclude live databases, process-owned files and
serving roots from writes. Integration requires a fresh drift comparison. Restore
only this task's proven changes using the inverse map/backup; never reset or stash
someone else's work. Branch names and atomic commits are optional user actions,
not an automatic safety mechanism or acceptance requirement.

Verification is proportional, not a full expensive suite after every small move:

| Change | Required checks |
|---|---|
| Navigation/docs | Link/path audit, archive hashes, no unrelated source drift |
| Independent scripts | Import/CLI smoke, root resolution and affected regressions |
| Builders/recovery tools | Fingerprint/old-command compatibility; defer if uncertain |
| Python tests | Collection parity, helper imports, affected tests |
| CJS tests | Actual Node suites and render/network contracts from documented cwd |
| Final structural integration | Appropriate Python regression, frontend build, evidence hashes, live HTTP smoke |

Reuse the release's unchanged evidence. Recheck native/personal hashes and process
identity after integration. Never generate BDS worlds, start searches or restart
live services just to verify a documentation move. No timing or artifact limit is
silently expanded. Report exactly what moved, stayed fixed and was deferred.

## 6. Acceptance and approval

Acceptance: useful navigation, only dependency-proven moves, original content and
history recoverable, no lost dirty/untracked evidence, preserved native/personal/
catalog identities, correct links/imports/commands, relevant tests passing and a
verified inverse move map. No commit/merge/push or deletion is part of this plan.

Before physical execution, present the reconciled High critique, exact first batch,
backup location, ownership, risks and checks for approval. Additional broad source/
test refactors are not implicitly approved by approving safe documentation moves.
The companion variant proposal has separate explicit validation/resource gates.
