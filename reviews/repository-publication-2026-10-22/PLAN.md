# Repository publication hygiene — 2026-10-22

User request: clean/organize the repository, push it to GitHub, and provide a prompt for independent Claude/Gemini audits.

## Scope and sequence

1. Inspect dirty state, instructions, handoff, existing safe organization, workers, process identities and remote. Preserve the full existing implementation/evidence; no new feature implementation.
2. Routine documentation hygiene only: refresh README and existing navigation, remove duplicate ignore lines without changing ignore semantics, add docs/audits/INDEPENDENT_REPOSITORY_AUDIT_PROMPT.md, and record publication scope/checks. Do not physically move source/tests/contracts/reviews or rewrite frozen evidence. Earlier approved eight-document organization remains intact.
3. Inventory candidate Git paths and scan for credential patterns, embedded private keys, generated/runtime data, broken tracked links and oversized files. Preserve local ignored runtime/dependency/build roots. Do not delete any files or silently omit implementation dependencies. Maintain a baseline hash manifest and verify only the listed routine documentation files change.
4. Independently review publication risks using one Gemini High, read-only, tool-free critique of this exact plan and context. Resolve findings using actual source/index state. The user explicitly requested commit/push; this is publication of existing implemented work plus small routine docs, not a new significant development/refactor plan. If significant implementation or new physical moves become necessary, stop that portion for a concrete reviewed approval.
5. Run meaningful existing catalog/native/personal selected regression tests and frontend checks, checking imported source paths. Reuse current historical full-suite evidence rather than claiming new all-project certification. Use bounded temporary output; do not run new searches/BDS or restart services.
6. Stage the explicit inspected allowlist including earlier approved document deletions/renames. Inspect staged paths, tree mode, size, diff, secret scan and dependency completeness. Commit with an accurate message and push current main normally to existing origin only if remote main remains baseline; never force push or rewrite history. Verify remote SHA and clean status. Record preservation and test evidence. No live service activation.

## Ownership, resources and acceptance

Codex owns documentation/index/staging/integration/verification/publication. Gemini only critiques the plan, no writable ownership or commands. Expected complexity low for hygiene, moderate for publication due to 1,132 existing untracked files (~78MB). Estimated 15–25 minutes. Read-only worker: 180-second limit, 2GiB RSS, no command execution.

Acceptance: no payload deletion, stable implementation/contract/evidence hashes preserved, no live/process change, credential/runtime exclusions inspected, documented limitations and audit prompt, selected checks pass or concrete preexisting failures reconciled, origin/main equals published commit, working tree clean for intended publishable files. Git ignored runtime stays local. Archive references to external private evidence must be distinguished from self-contained repository verification; publication cannot manufacture missing evidence.

## Initial state

main HEAD and remote main: fd36d4dc3b86581858ff75e91df187eac088862c. Origin git@github.com:lucasraicu/minecraft-seed-searcher.git. Existing 54 tracked modifications/deletions, 1,132 untracked files. All untracked files are under root documentation, docs/, fixtures/, reviews/, scripts/, src/, tests/, web-ui/. Largest file ~21MB; no >50MB new file. Eight historical documentation moves already approved/applied. No worker running. Personal91321/public22035/Vite17880 present; no restart allowed. gh executable absent, ordinary Git SSH remote read succeeds.

Current readiness result: private optimizations verified, not activated in live process; original summaries.py unchanged. Sustained 67,122 personal INPUTS/sec under 34-thread search plus one catalog extraction worker and two mostly-cache-hit HTTP clients; public records ~45s sequential, one existing world replayed, not new discovery rate. Isolated optimized record median24.97s. Natural 100-candidate heap scaling unmeasured. GPU contract only; no kernel. SQLite remains control store, private patched runtime tested but live interpreter unchanged.
