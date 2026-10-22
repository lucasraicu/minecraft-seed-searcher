# Codex + Antigravity project workflow

Codex is the primary orchestrator in the user's existing VS Code chat. Read
`CODEX_HANDOFF.md` on session start and reconcile it with actual Git, workspace,
process and worker state. The handoff records facts; it does not grant approval.
Preserve inherited instructions, including the global final-task notification.

## Planning and approval

For substantial development, inspect relevant instructions, code, specifications,
dirty Git state and affected processes first. Reuse existing reports, tests and
benchmarks. Produce a plan stating objective, architecture/files, proposed changes,
dependencies/order, independent tasks, risks/conflicts, tests/benchmarks, acceptance
criteria and relative complexity/resource needs.

Have one or two Gemini workers independently critique significant/nontrivial
plans at High reasoning. Give neutral prompts and relevant evidence; ask for
missing cases, alternatives and correctness/performance risks. Resolve objections
using source evidence and tests; do not automatically accept worker conclusions.
Present the final plan, assignments, consequential disagreements and unresolved
risks to the user for approval **before significant implementation**. Do not
implement until approved. Small routine fixes use a lightweight internal plan
without unnecessary approval. Preserve any additional applicable approval gate.

## Delegation and integration

Codex owns architecture, decomposition, scheduling, delegation, conflict
resolution, integration, final validation, reporting and handoff. Use **zero to
four** Gemini workers through `antigravity-workers`, according to useful task
independence. Four is a ceiling. Do not duplicate questions/work without a reason,
overlap writable ownership, recursively delegate, or run uncontrolled agent chats.
Workers may implement, debug, optimize, test, research or independently review
native C, Python and React/TypeScript work.

Every worker receives a bounded objective, relevant context, explicit acceptance
criteria, file ownership, time/resource limits and exact permitted commands.
Coding uses isolated snapshots/worktrees that include relevant uncommitted
changes without modifying the primary workspace. Ignored dependency environments
are not copied automatically; prepare suitable isolated dependencies when needed.
Keep prompts focused, results concise and retries/timeouts bounded. Reuse verified
findings rather than retransmitting the repository or repeatedly reviewing plans.

All Gemini roles must explicitly use **High reasoning**. The installed bridge
uses `gemini-3.8-flash-high --effort high`; verify support for any future model.
Never silently lower effort or change models to work around a limitation; explain
unsupported settings/model changes. Interactive defaults are not headless proof.
Codex reasoning is selected manually by the user in VS Code; prefer High for
complex reasoning and Medium for routine coordination, without dropping checks.

Poll submissions to terminal state and inspect actual exit/JSON/response,
`denied_actions`, usage, checks and patches. Empty SUCCESS, denied required actions
and self-reported success are insufficient. Codex independently reviews important
results and disagreements before integration. Integrate only approved work,
preserving unrelated edits. Never automatically merge, push or overwrite the
primary repository; workers must never merge or push. Do not reset, stash, clean
or overwrite existing work without authorization. Do not use
`--dangerously-skip-permissions` or unrestricted filesystem/shell permissions.

### Credit preservation mode ("Offload to Antigravity")

When the user issues the single-line directive **`Offload to Antigravity`** (or directs Codex to preserve credits / delegate heavy lifting):
1. **Cease Direct Token-Heavy Work:** Codex must immediately stop reading large files into the chat window, generating lengthy multi-page specifications/configs, or running autonomous multi-turn tool loops directly.
2. **Delegate via `antigravity-workers`:** Package the task (research, file inspection, extensive writing, test execution, or patch implementation) with bounded objectives and dispatch it to Gemini High workers via `antigravity-workers`.
3. **Crucial Cost Distinction:** Tasks run in Antigravity consume Google account quota and cost **zero OpenAI/Codex credits**. Codex remains strictly a lean orchestrator, reviewer, and final integrator in VS Code, protecting the user's Codex token limits.

## Verification and shared quota

Select meaningful checks for the components changed: Python tests, native builds,
C/Python parity, frontend build/UI checks, regression/integration checks and
Bedrock verification where applicable. Do not run expensive checks unnecessarily.
For optimizations, establish a reproducible baseline, use comparable conditions,
verify correctness and report measured performance. Distinguish preexisting from
introduced failures; never silently weaken acceptance criteria or tests.

Workers share the authenticated Google account and quota. On quota/auth failure,
stop new dispatches, retain results, record the interruption in the handoff and
inform the user. Do not switch accounts, bypass limits or repeatedly retry
exhausted workers. Resume explicitly only after confirming that the same account
is ready. Track usage where exposed; do not invent remaining-quota estimates.

## Handoff, recovery and communication

Maintain concise, factual `CODEX_HANDOFF.md` sections A–J: project overview,
current objective, approved plan, progress, worker activity, repository state,
verification, decisions/risks, next actions, and environment/recovery. Record task
IDs, agents/statuses, ownership/workspaces, evidence, actual approvals, High
verification, blockers and next executable steps. Preserve accurate older records;
do not invent approvals, results or completion. No credentials or bulky logs.

Update after meaningful milestones, plan changes, worker completions or failures,
and before intentional termination/account switching when possible; avoid minor
rewrite churn. Do not automatically commit/push the handoff. Before switching,
checkpoint active work safely, record running tasks/partial results and recovery
steps; do not terminate active processes without authorization or safety need.
Never switch Codex or Google accounts automatically. A fresh session must read
instructions/handoff, inspect Git, verify MCP/task availability, reconcile stale
records, avoid duplicate work and resume only user-approved work. Actual state
takes precedence. Ask only for necessary clarification or required approval.

Show concise milestone updates, important failures and disagreements in the
existing chat. Before substantial execution show the objective, approach, critique,
assignments, risks and approval request. Afterward report changes/files, worker
contributions, verified tests/benchmarks, limitations and remaining steps. Summarize
logs and distinguish independent verification from worker claims.

Orchestration setup does not authorize new seed searches, modifications to active
experiments or a new implementation project. Finish setup, then await the next
development objective.
