# Stage D shared evidence integration — 2026-10-20

Completed the reviewed evidence steps1–3 after the user-selected supported-type BDS
cohort. This does not mean every prediction passed the game audit. Estimated-spawn
codec migration and native predictor corrections remain subsequent work.

## Result

Existing Catalog preview: http://127.0.0.1:5173/#catalog . Original Sweep remains
on3000. Owned Catalog backend refreshed on3001; no separate website was created.
The original28-village result now carries28 predictions,27 exact BDS location
matches and1 coordinate disagreement. Research ranking still uses predicted counts;
confirmed-location totals are not represented as complete physical village counts.

All five live Rare research lists use shared per-feature evidence summaries.
Personalized detail scopes evidence to its selected anchor and border.16 Presets
and22 named Rare records remain gated. Grouped temple checks identify generic
locations; they do not certify desert/jungle/hut/igloo subtype generation. Biome API
observations are retained with sampling interpretation explicitly unresolved.

## Changes

- `src/seed_search/catalog/evidence.py`: versioned strict schema, source identity
  binding, bounded raw checks, checksummed immutable no-clobber publication,
  durable directories/files, symlink rejection and partial/scoped summaries.
- `scripts/catalog_evidence.py`: bounded offline importer validates pinned image,
  observed seed/build/settings, cleanup, source membership and raw command outputs;
  conflicting repeated results fail closed. No serving-time seed computation.
- `service.py`: annotates research results and same-layout detail; missing evidence
  is untested, corrupt evidence is503. Raw observations and ranking stay unchanged.
- Shared React `EvidenceSummary`, response-count validation and Rare/detail wiring.
  Missing evidence, partial checks and grouped-command limitations remain visible.

Published four immutable sidecars under the existing private catalog's `evidence/`:
185 registered-structure checks and586 catalog-coordinate biome observations.
Nether/End, independent discovery and non-catalog/vertical controls remain in the
raw audit report; they are not misrepresented as existing Overworld catalog fields.
Current v1 sidecars are immutable per snapshot/world. Additional evidence for an
already-published pair requires a new snapshot/versioned release; the importer
refuses an overwrite. No mutable verification job database was introduced.

## Verification

- **280 catalog Python tests passed**,155.92s; includes33 focused evidence/API/import
  cases. The33 are included, not additional to280. Tests cover bad provenance,
  malformed/count/command checks, unknown vs failed, immutable/racing publication,
  corruption, symlink ancestors, fsync failures and circle/square border edges.
- New shared-component SSR tests, response-decoder tests and integrated Rare list
  render tests passed; existing four-pillar/UI contract tests passed.
- TypeScript and production Vite build passed, output isolated outside the project;
  original live `web-ui/dist` was not replaced. Browser visual/keyboard QA remains
  deferred by the user's earlier explicit instruction.
- Independent raw-BDS oracle checked all477 returned rows across the five lists;
  summaries agreed. Combined service-check runtime0.31s is a local warm observation,
  not a general performance guarantee.
- Actual HTTP3001 and Vite proxy5173 return27exact/1disagreement for the original
  seed.200worlds/48600layouts and all200 observation IDs remain unchanged.
- Original Sweep PID60144/startOct16 and Vite22102 preserved; owned backend22084
  gracefully replaced by24886/session81507. Both native binary SHA256 values match
  the preexisting baseline. No seed jobs/game containers remain. No commits/pushes.

## Gemini contributions and Codex review

High critiques10fc702886ba/833bb6471b3d and analysis ef69bede9c65 informed test design;
Codex rejected unsupported terrain-cause, tolerance, sampling-height and global
accuracy claims. Codex executed and independently parsed all actual BDS probes.

High UI worker39b7afbfaf94 succeeded, exit0/denied[], only2ownedfiles changed, declared
node syntaxcheck passed. Codex ran semantic SSR tests, removed silent success on
missing dependencies, tightened fields and compacted the display. Reported usage
206122tokens; no remaining-quota estimate is inferred.

High core worker49947ab2dc63 timed out at480s and was not accepted as a worker
success. Only its2ownednewfiles were present. Codex inspected the partial source,
repaired ancestor-path/durability/bounded-read/type/resource handling and a worker
test that confused a missing path with artifact substitution, then independently
validated all behavior. No timeout/empty SUCCESS was presented as completion.

## Remaining correctness work

BDS type audit is not a universal pass. Raw block/quart biome sampling and cave
eligibility need further source-backed diagnosis; coordinate conventions require
explicit validated adapters; abandoned camp lacks a successful locate control;
End classes and grouped temple subtypes need suitable independent observations.
No physical structure census or complete recall has been established. Keep these
claims gated. Spawn migration is the next dependent Stage D step, preserving the
reviewed estimated-world-spawn versus exact-player-spawn distinction.

External evidence and preservation/oracle/HTTP/build artifacts:
`~/.local/share/antigravity-worker-mcp/catalog-all-predictions-audit-20261020/`.
See [REPORT.md](REPORT.md) for the game-audit table and [PLAN.md](PLAN.md) for scope.
