# Independent review and Codex reconciliation

2026-10-21. Planning evidence, not implementation or accuracy certification.

## Worker results actually inspected

- `d9bdd633f1e8`: succeeded, Gemini `gemini-3.8-flash-high`, effort `high`,
  process exit0, nonempty response, denied_actions[], changed_files[], checks[].
  Usage18,058 total tokens (input14,754/output3,304; reported thinking2,279).
  Independent automation critique supports the architecture with explicit
  frontier/geometry/schema/GC contracts. No tests or commands ran.
- `8eab34b09e7c`: bridge state **failed** because the literal response marker was
  missing. Provider SUCCESS/exit0 and actual nonempty review do not override
  that status. Gemini same High model/effort; denied_actions[], no edits/tests.
  Usage18,755 total tokens (input15,437/output3,318; reported thinking2,067).
  Retained as supplementary critique only; not claimed as a successful worker.
  No retry required: one successful independent High critique satisfies AGENTS.

Actual returned structured results are preserved in REVIEW_<task_id>.json.
Neither task had quota/auth failures or permission denials. No remaining quota
estimate is inferred. No implementation work or changes were integrated.

## Findings and resolutions

1. Farm names: agree that XZ clusters cannot certify simultaneous Bedrock farms.
   Strengthened scope to keep Technical Redstone & Farms gated, and put optional
   geometric candidates in Structure Clusters. The review's specific simulation
   distances, spawn radii, hut block positions and portal-search radii were not
   source-backed in its supplied evidence. They are not adopted as verified facts
   or used as product rules. No need to resolve them to defer farm guarantees.
2. Nether anchor: agree a projected coordinate is not the actual starter portal.
   Plan now specifies a distinct `projected_overworld_anchor_nether` tag. Original
   starter-portal predicates remain gated. No portal displacement bound adopted.
3. Survey boundary: reject the feasibility review's assumption that stored public
   observations stop at radius2000. `summaries.py` and the public registry use the
   full [-5120,5120) square. Origin-r2000 is a record query scope, not extraction
   coverage. Still enforce containment for each spawn-centered requested scope;
   enrich or leave pending outliers, rather than discarding promising seeds.
4. Village subtype: agree and already excluded from simplified promises. Explicit
   structure-start/biome-witness semantics remain; a plains witness does not
   establish village architecture. Missing subtype evidence cannot be relabeled.
5. Product IDs: accepted clarification. Distinct weaker-product IDs, accurate names
   and revisions protect old promises; no quiet replacement under a stronger ID.
6. Retention explosion: agree with caps/registered combinations, but reject the
   architecture review's suggestion to restrict all objectives to16presets+22
   records. That would remove personalized specialist/diversity/sample coverage.
   Retain the existing bounded objective families and add only budgeted registered
   public products; unsupported originals and28undefined records stay gated.
7. Determinism: compare squared distances without float rounding. Within a world,
   choose best qualifying anchor with an explicit stable anchor-ID tie, then rank
   unique worlds by product metric and world ID. This prevents one seed occupying
   many slots; acceptance compares stream results to an independent full sort.
8. Frontier and GC: adopted/retained durable intake before personal rejection,
   independent public progress and explicit sampling/unevaluated ranges, durable
   artifacts before manifest publication, fail-closed reachability and pin/cursor/
   reader protection. Existing published snapshots remain protected. Bounded disk
   implies pause unless a separate published-snapshot expiry policy is approved.

## Execution boundary

Only planning/review documents and the factual handoff changed. Existing dirty
project work, native artifacts, snapshots and services were preserved. Processes
77988(personal3000),77098(catalog3001),77100/77101(query workers),65292(Vite5173)
were observed alive at reconciliation. No seed search, BDS run, benchmark, service
restart or code change was performed. Source inspection, not a new accuracy test,
supports this classification.

User has authorized the overall automation direction and Pillar3 additions.
Specific simplified product contracts and new default scopes/capacities in PLAN.md
are proposed for approval before significant implementation. This review does
not complete full automation or alter the approved earlier accuracy results.
