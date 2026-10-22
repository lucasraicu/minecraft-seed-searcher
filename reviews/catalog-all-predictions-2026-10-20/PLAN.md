# BDS validation before Stage D — 2026-10-20

User instruction: test all biome/structure predictions with BDS before continuing
Stage D; Gemini concurrency explicitly permitted. This authorizes the expanded
validation objective and subsequent Stage D sequencing. No new seed-search campaign,
private-world modification, automatic push or weakening of verification is inferred.

## Frozen inventory and scope

Existing snapshot3d964acd07729a1aa50c23ba90e90a37754c009fc685f0313cc6cf0157eddd6a:
200 worlds,517041 retained structure predictions across14 Overworld structure types,
5120000 XYZ biome points,9 selectable biome families. Broader backend supports22
structure types; unsupported/unrepresented types need separate controls and must not
inherit catalog validation. Test catalog observations once per world, not243 layouts.
All stored points means the full inventory; a small pilot is not completion.
No claim to testing every possible seed/block or complete physical structure census.

## Execution and architecture

Codex owns inventory, bounded pinned-BDS harness, raw-result review and integration.
Two independent Gemini High read-only critiques run concurrently: biome semantics
and structures/recall. Application sources, native binaries, primary SQLite and
serving dataset remain unchanged during audit. External checksummed evidence and
checkpointed query records bind exact seed, world/observation hash, settings,
image/build, dimension, XYZ and method. Keep research26.50 predictor identity distinct
from actual BDS1.26.52.3. Failures, unknowns and mismatches stay separate.

First executable batch: one existing known seed, up to3 closest retained predictions
per represented structure type,256 central stride64/Y63 biome points. This measures
load/disk/response behavior and verifies command IDs before full inventory dispatch.
One disposable BDS process only: Docker currently4CPU/about8GB RAM; cap2CPU/5GiB,
600seconds,1000commands,8GiB owned output, no published ports. Container-local timeout,
unique ownership labels, exact image SHA check, exact world.seed observation and
owned-only cleanup. Preserve raw failures, never silently retry/replace cohort.
Check resource cap between bounded16-point biome batches. Script queries sameXYZ;
if unloaded, creates bounded one-column ticking areas in this disposable world,
then removes them after batch. No terrain fixture edits. Stop for capability failure,
output/time cap, failed cleanup or systematic verifier error before larger dispatch.

After pilot: estimate full-inventory costs from actual measurements and report
remaining feature/seed/control gaps. Freeze a resumable, capped partition manifest
before larger runs. No promise that full-catalog validation fits a single session.
Do not silently substitute a representative sample for the requested full inventory.
Structural command-coordinate agreement is not generated-building certification;
independent discovery probes are sample recall evidence, not exhaustive recall.
Four temple subtypes share official `temple` command: exact-coordinate matching
confirms an engine temple location, not its subtype. Missing controls remain gaps.

## Acceptance and Stage D sequencing

Per-feature matched/tested/unresolved counts; biome raw names plus documented aliases,
exactXYZ/height semantics, per-family coverage/confusion; capture no-hit/error output.
No fitting coordinate tolerance after seeing results. Physical-building evidence,
subtypes, Y, terrain and loading/farm claims need separate verified methods.
Boundary and independent-discovery controls complement positive-coordinate checks.
Save known village mismatch as regression evidence. Do not claim100%generalaccuracy
from third-party markers, selected seeds or agreement-only samples.
Stage D (shared versioned evidence, API/UI, then estimated-spawn migration) proceeds
only after validation results and remaining gaps are explicitly reconciled. Unknown
or failed features stay gated; validation need not force silent algorithm changes.
Any native bug fix requiring substantial implementation gets its own scoped review.

## Gemini critique and reconciliation

Biome10fc702886ba and structures833bb6471b3d both completed model
 gemini-3.8-flash-high, reasoning_effort high, exit0/SUCCESS, denied[], files[].
They reviewed supplied facts tool-free; did not execute BDS or independently audit
source. Accepted: exactXYZ matching, per-feature controls/provenance, distinct recall,
measured resource pilot and strict locate-versus-physical distinction.
Corrected supplied inventory assumptions13types/10families to actual14/9.
Rejected unmeasured disk/runtime estimates, claims that every biome point forces
all envelope chunks, unsupported exact locate offsets/ranges and arbitrary matching
tolerances. Reject declaring the village physically absent purely from locate.
Actual sampled chunks total at least one per unique coordinate chunk if loading is
needed, but neighbor generation must be measured. No invented population accuracy
or generic 4–8block uncertainty allowance for exactXYZ biome tests.

Relative complexity: capability pilot moderate; fullinventory potentially large,
resource-bound; Stage D evidence/schema moderate and spawn versioning moderate/high.
ETA for whole campaign awaits pilot; no unfounded fixed completion date.

## User scope clarification and execution checkpoint

User chose **all supported types first, then expand based on results** in the
async scope question. Literal517041/5120000 complete-point sweep is no longer the
initial requirement. Freeze a three-world stratified type cohort, at most3 predicted
locations per22 structure types/world, up to2 retainedY63 points per56 Overworld
biome names/world, plus Nether/End capabilities. Max600seconds/world, serial BDS.
Seed cohort3477702448211353566,-4565879772552070118,-9103892851552028103.
All22 engine structure types have candidates in this cohort; chosen worlds have
mansion controls and broad biome diversity. This is deliberate feature coverage,
not an unbiased population accuracy sample. Independent fixed discovery probes in
later runs check for omitted locations but cannot establish exhaustive recall.
End internal terrain classes are not automatically separate BDS biome identifiers.

Pilot completed:39 structure commands,256Y63 biome observations,239 canonical matches,
17 sameXYZ differences,0 biome errors;259.56s; clean cleanup. No algorithm fix or
StageD implementation before validation. Existing aliases reused; name variants
are not automatically defects. No tolerance-fit or unsupported terrain-cause claim.

Additional Gemini High analysis ef69bede9c65 completed exit0/SUCCESS denied[] files[],
20348tokens. Useful source convention clues; reject worker assertion that17/256
sameXYZY63 biome differences are explained by comparingY319 againstY63 (we compared
Y63 againstY63), reject unproven terrain-failure cause and arbitrary24block pass
radius. Small coordinate shifts are observations/hypotheses, not blanket matches.
