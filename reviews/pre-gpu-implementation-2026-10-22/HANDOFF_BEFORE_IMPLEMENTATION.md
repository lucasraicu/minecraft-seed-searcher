# Minecraft Seed Searcher — operational handoff

Updated 2026-10-22 (America/Los_Angeles). Reconcile with live state before resuming.
This is a factual checkpoint, not authorization for additional work.
Historical log archive (Oct 15–22, 2026): [docs/archive/CODEX_HANDOFF_ARCHIVE_20261022.md](docs/archive/CODEX_HANDOFF_ARCHIVE_20261022.md).

## A. Project Overview

Bedrock seed prediction/search with a native C11/CFFI/OpenMP engine (`native/`,
`vendor/cubiomes-bedrock/`), Python orchestration, scoring and SQLite persistence
(`src/seed_search/realm/`), HTTP control plane (`src/seed_search/web/server.py`),
and React/TypeScript UI (`web-ui/`). CLI: `src/seed_search/cli.py`.

Runtime reference: [README.md](README.md),
[MASTER_SEED_BLUEPRINT.md](MASTER_SEED_BLUEPRINT.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).
Platform/product plans: [MASTER_PLATFORM_SPECIFICATION.md](docs/specs/MASTER_PLATFORM_SPECIFICATION.md),
[PUBLIC_CATALOG_SYSTEM_SPEC.md](PUBLIC_CATALOG_SYSTEM_SPEC.md),
[PUBLIC_CATALOG_PLAYER_POLICY.md](docs/catalog/PUBLIC_CATALOG_PLAYER_POLICY.md),
[PUBLIC_CATALOG_IMPLEMENTATION_PLAN.md](PUBLIC_CATALOG_IMPLEMENTATION_PLAN.md),
[DUAL_HARVEST_GPU_CATALOG_ARCHITECTURE.md](docs/specs/DUAL_HARVEST_GPU_CATALOG_ARCHITECTURE.md).
Deployment guide: [SERVER_SETUP_GUIDE.md](SERVER_SETUP_GUIDE.md).
[Catalog contracts](docs/catalog/v1/README.md) explicitly remain proposed, with
runtime/billing activation false. Planned throughput/storage claims in design
specifications are not independently verified by this setup.

## B. Current Objective

COMPLETED — pre-GPU readiness audit and reviewed plan, 2026-10-22.
User requested current-state review and plan, not implementation.
Plan: [PRE_GPU_READINESS_PLAN.md](docs/PRE_GPU_READINESS_PLAN.md).
Evidence: reviews/pre-gpu-readiness-2026-10-22/ (audit, checks, critiques, reconciliation).
A reference freeze; B checkpoint/derivation and C guarded read views in parallel;
D recovery/sustained acceptance. E GPU contract/confirmed hardware and isolated
one-device proof can proceed after A without waiting for serving C/D. Integration
at scale requires both tracks. F engine comparison conditional; no winner selected.
All implementation/resource allocations remain PROPOSED, not approved or started.
Fresh: 638 catalog tests collect, 26 focused tests pass; legacy contracts validate;
208 source/build/state hashes and service identities preserved. Prior full 637-test
pass is reused, not relabeled as a current full-suite run. Known fork-test warning.
Two High reviews 1ff842502952/c3dfcdfb5058 succeeded, exit0/denied[]; reconciled.
0 workers running, no account pause. Current host AMD Vega56/8GB; future CUDA host unverified.
Previous benchmark/profiling, variants and eight-document organization are complete.
Profiling report: reviews/storage-query-profile-2026-10-22/REPORT.md (32.43s record,
2.25–4.59s generic misses; serialization/read views first, retain SQLite control).

COMPLETED EXECUTION — 2026-10-22. User attachment d5361274 explicitly approves
PUBLIC_CATALOG_BIOME_EXPANSION_PLAN.md including section 5a 2x reserve and expandable
UI. Earlier awaiting-approval entries are archived. Active goal created by /goal;
no repeated approval required for this reviewed scope. Codex owns review, personal
reserve, storage/migration/evidence/integration; delegate scoped coding to Gemini High.
Baseline: external biome-expansion-approved-20261022/baseline with relevant dirty source
and baseline-hashes.json. Live personal 91321, public 18349, Vite 17880 verified;
no worker running or account pause. Preserve personal processes, DB/checkpoints/native
binaries and historical catalog. No new seed search.

LATEST PLAN AMENDMENT — 2026-10-22. User asked whether the entire personal/public
sweep can retain a 2x reserve before displaying finalists. Added section 5a of
PUBLIC_CATALOG_BIOME_EXPANSION_PLAN.md; no runtime changes. For target K retain 2K
total distinct worlds, display K primary, remainder reserve per objective. Personal
50->100 must change the tracker/native cutoff as well as checkpoints; old-capacity
runs cannot silently resume at 100. Public proposed 115,964 primary slots -> 231,928
retained slots, same 7,543 objectives. Policy-bound harvest.py/store.py guards and GC
must protect all reserves. Generic search uses the retained union; objective roles
are not global seed flags. No BDS budget increase or automatic verification campaign.
High review 11d530d30c6c succeeded, exit 0/denied [], no changes/tests. Total plan
review usage 81,028 reported tokens; no quota/auth pause.

CONCURRENT BEDROCK SERVER DEPLOYMENT GUIDE — 2026-10-22. Complete production deployment
specification generated in `SERVER_SETUP_GUIDE.md` for 20-player BDS (2048x2048 Overworld,
1024x1024 Nether, VCMC voice chat, BedrockAdvancements, Land Claims, Clear Glass, Brewing Guide,
GraveStones, and Twixxel's Stalkers calibrated to 6 hearts / 30-min cooldown, chunk pre-gen,
automated backups with logging, and allowlist security).

## C. Approved Plan

Readiness implementation is proposed only; user approval is required before coding.

Completed biome plan: [PUBLIC_CATALOG_BIOME_EXPANSION_PLAN.md](PUBLIC_CATALOG_BIOME_EXPANSION_PLAN.md).
Scope: 56 individual Overworld biome choices + 5 existing Nether choices + 4 groups.
Core 46 OW choices reuse Y63; 10 mountain/cave choices gated on compatible height evidence.
Two auxiliary predicted-basement/treasure-bastion filters conditional on existing-method controls;
stronghold investigation/report only, no predictor change. Preserves 845/265/140 budgets,
personal state, three sizes, and legacy product rules.
Historical plan approvals from 2026-10-15 through 2026-10-21 preserved in `docs/archive/CODEX_HANDOFF_ARCHIVE_20261022.md`.

## D. Progress

CURRENT ADOPTED SUCCESSOR — public PID22035/3001 serves external
`treasure-activation-approved-20261022/catalog` under persistent worker data.
Snapshotcd76367cbd7a679322048d534821f3017e98c9d7f57e7569568f65183074109d;
policy1b3ff7b9cd1897444ff3747825c7f1ac6eba4ccbcc544b2a0f6ff23a39835e9b.
222worlds /109918memberships: all109438old +480new across12variant lists.
All56Overworld choices,4groups,5Nether choices and both auxiliary variants enabled.
7543objectives,115964primary/231928retained capacity remain unchanged.
Public automation paused0/600s, no jobs/campaigns. Historical snapshots keep gates.
Original public root `biome-expansion-approved-20261022/catalog-corrected` retained
for rollback with snapshot9637bc21753fa249775f0b11e84ec7a9a92d3872d7982f8e3dfd9a2be4859421.
Original biome migration completed3617.6/3780s; current task uses separate approved
bounded allocation. No budget reset. All work in the approved safe scope complete.

SERVER DEPLOYMENT GUIDE PUBLISHED — [SERVER_SETUP_GUIDE.md](SERVER_SETUP_GUIDE.md)
remains the separate concurrent deployment deliverable; no server deployment was
performed by the biome expansion release.

## E. Gemini Worker Activity

Latest High critiques: 1ff842502952 (correctness/recovery) and c3dfcdfb5058
(performance/storage). Both succeeded with exit0/denied[], no edits/tests.
Codex reconciled source and measurement objections; see readiness RECONCILIATION.md.
Reported review usage 41,948 tokens; remaining shared quota unknown, no pause.
Previous worker IDs and results remain in the saved pre-readiness handoff and
release evidence. All workers terminal; no active tasks/subagents.

## F. Repository State

Working tree has uncommitted dirty changes across engine, catalog, tests, and web-ui (tracked in git status).
All inherited dirty work preserved; no `git reset`, `git stash`, `git clean`, or unauthorized merge/push.
Key uncommitted reference files: `SERVER_SETUP_GUIDE.md`, `PUBLIC_CATALOG_BIOME_EXPANSION_PLAN.md`,
`docs/archive/CODEX_HANDOFF_ARCHIVE_20261022.md`.
Native binaries and SQLite databases preserved intact.

## G. Verification

Current successor:66focused Python tests;25biomeUI+17productUIchecks pass.
Independent audit:222worlds,54615summaryrows,109230variant oracles,all109438old
memberships,480new members and6808immutablehistorical files pass.
Portable fixture137members /48staticchecks pass; archiveSHA
ab4d7a9cbf53781db8d8d51f9f5a8877dcb329d3a39c484690905dccc985aaea.
Both real metadata gates render correctly;4actual product responses decode.
460navigationlinks,199protectedfiles and57nativefiles pass. Full details in release.
Prior biome verification (unchanged components):
Final release:637catalog tests pass285.47s, later8startup/metadata tests pass.
Independent222world coordinate/history/legacy audit PASS;7027existing-objective2K
full-sort replay PASS;504atomic objectives pass oracle audit,12gated lists empty.
Nine mixed HTTP queries2.60–4.98s;12row/16OR stress6.15s. All36products/72responses
pass actual frontend decoder; paging/view cursor isolation and historical shares pass.
Live adopted query/detail4.84s/4.67s, snapshot listing0.55s; Vite proxy correct.
199protected files,57native sources, legacy ASTs and11legacy JSON contracts unchanged.
All10catalog Node suites,25UI checks/network/telemetry and build pass;12UI source hashes
unchanged since verified build. Browser interaction waived. Details/evidence in release.


1. 81 recovery checks pass (24.30s), protected 199 files verified unchanged.
2. 39 focused catalog/service tests pass (12.64s).
3. 23 native guard / independent refinement tests pass (5.04s).
4. All 36 real product responses decode successfully in frontend decoder.
5. Server setup guide verified: addon size ~5.1 MB, simulation distance capped at tick-distance=4,
   Stalker calibrated to 7 hearts (14 HP), guaranteed 1-hit vanish, and 30-min cooldown (36000 ticks), backup logging verified.

## H. Decisions and Risks

1. **Reserve Policy (Section 5a):** 2x distinct candidate retention per objective; primary K displayed,
   remainder held in reserve. Prevents candidate loss during catalog updates.
2. **Tick Distance Ceiling:** Server tick-distance must remain at 4 chunks (81 simulated chunks/player)
   to protect 20-player TPS. Never raise to 6 chunks.
3. **No Teleportation:** Survival integrity strictly enforced; claim warp buttons removed, GraveStones
   does not offer teleports.
4. **Stalker Balance:** Fixed at 7 hearts (14 HP) with guaranteed 1-hit vanish (`entity.remove()` on contact)
   to eliminate double-hit bugs; unarmored players survive at 3 hearts, iron armored players take ~2.8 hearts.
   Strictly Overworld only with 30-min cooldown.
5. **Context Window Protection:** Older verbose handoff logs archived to keep active handoff under 200 lines,
   protecting Codex from 55k-token context inflation on startup.
6. **Credit Preservation Directive ("Offload to Antigravity"):** Per `AGENTS.md`, whenever the user
   types `Offload to Antigravity`, Codex halts direct file reads, large text generation, and multi-turn
   loops in VS Code, immediately delegating heavy tasks to Gemini High workers to protect OpenAI/Codex credits.

## I. Next Actions

1. **Readiness plan:** Await implementation approval. Next executable work is A; then B/C
   and E contract can proceed independently. No new compute allocations are approved.
   Profiling, benchmark, variant/organization and biome releases are complete; preserve rollback evidence.
2. **Seed Finalization:** When the final certified God Seed is chosen, compile `Server_Milestones.mcpack`
   with the exact centroid coordinates $(C_X, C_Z)$.
3. **Launch Day Server Prep:** Run chunk pre-generation across the 2048x2048 Overworld before players join,
   configure `allow-list=true` with the 20 player Gamertags, and schedule `backup.bat` / `backup.sh`.

## J. Environment and Recovery

Active persistent services:
- **Personal Server:** PID 91321 on `127.0.0.1:3000` (started Oct 16, preserved)
- **Catalog Server:** PID 22035 on `127.0.0.1:3001`, both-variant successor root
- **Frontend UI:** Vite PID 17880 on `127.0.0.1:5173` (`http://127.0.0.1:5173/#catalog`)

Python Environment:
- Python 3.13 via `.venv/bin/python`
- Run tests: `.venv/bin/python -m pytest <test_path>`
- Frontend build: `npm --prefix web-ui run build`

MCP Workers (`antigravity-workers`):
```sh
codex mcp get antigravity-workers
/Users/lucasraicu/.local/share/antigravity-worker-mcp/.venv/bin/python /Users/lucasraicu/.local/share/antigravity-worker-mcp/mcp_client.py gemini_worker_status '{}'
```
Rules: Bounded objectives, explicit acceptance criteria, isolated snapshots, ceiling of 4 workers,
all Gemini roles explicitly use High reasoning (`gemini-3.8-flash-high --effort high`).
Do not automatically commit or push.
