# Stage D evidence overlay interfaces

Approved objective: validate all supported types first (user clarified cohort scope),
then continue Stage D. Initial integration is evidence steps1–3 of the reviewed
reviews/catalog-evidence-audit-2026-10-20/PLAN.md; native prediction changes are not
inferred from small coordinate disagreements or a fitted tolerance. Spawn migration
is the next dependent step, with its own versioned codec work, after evidence.

## Python evidence module (worker ownership)

Own only src/seed_search/catalog/evidence.py and tests/catalog/test_evidence.py.
No serving changes, native changes, schema migrations or raw-observation rewrites.
Use stdlib and existing catalog models/registry; avoid backend/native imports.

Functions:

- build_evidence(observation, snapshot_id, verifier, structure_checks, biome_checks=[]) -> payload.
- validate_evidence(payload, *, observation=None) -> same payload or ValueError.
- write_evidence(root, payload) -> pathlib.Path; immutable checksummed JSON.
- read_evidence(root, snapshot_id, world_id, observation_id) -> payload|None; missing
  is None, corruption/provenance mismatch raises ValueError, never silent fallback.
- summarize_structure(payload_or_none, feature_id, predictions, *, total_count=None) -> summary.

Payload exact keys: revision='catalog-evidence-v1', snapshot_id, world_id,
observation_id, source_identity, verifier, structure_checks, biome_checks.
IDs are lowercase64hex; source_identity is the full unchanged validated predictor
identity. world_id/observation_id derive from the supplied observation. Source and
BDS builds deliberately remain distinct; do not promote research26.50 identity.
Verifier exact keys: edition='bedrock', game_build_id (nonempty exact BDS build,
never research:*), image_sha256 (64hex digest without sha256: prefix),
script_api (nonempty string), settings_sha256 (64hex), report_sha256s (1..32 unique
64hex). No credentials/paths in this schema. source_identity/world_id must agree.

Structure check exact keys: feature_id, command_id, predicted, reported, outcome.
feature_id must be a registered catalog structure feature (14 Overworld types).
predicted=[intX,intZ] must be in source observation; reported is [intX,intZ]|null.
No bool coordinates; safe coordinate bounds abs<2**30. Unique(feature_id,predicted).
command_id is explicit pinned adapter: village,trial_chambers,ancient_city,mansion,
monument,pillager_outpost,temple(desert_pyramid/jungle_temple/swamp_hut/igloo),
trail_ruins,ruined_portal,shipwreck,mineshaft. Reject command/feature mismatches.
outcome is exactly located_exact (reported==predicted), coordinate_difference
(reported nonnull and unequal), no_location (reported null), or error (reported null).
No coordinate tolerance, global verified status or automatic transform matching.
Preserve disagreement/no-location as unresolved, not physical absence.

Biome check exact keys: position=[intX,intY,intZ], observed_name=string|null,
outcome='observed'|'error'. position must occur in source observation, uniqueXYZ.
Observed implies nonempty string; error implies null. Save raw names and observations;
biome API/block-sampling semantics remain unresolved, so do not certify witnesses.
Validate source-point membership in build_evidence/validate(observation=...).
Max10000 checks/type, max16MiB serialized envelope. Bound list/string lengths.
Validate exactly allowed keys and types, source hash consistency when observation
provided, point uniqueness and in-source membership. Don't mutate caller data.

Persistence: root/evidence/<snapshot_id>/<world_id>.json, envelope exact keys
sha256=digest(payload),payload. Reject symlink components, malformed/oversize JSON,
duplicate JSON keys, nonfinite numbers. Immutable existing same payload is okay;
different existing payload raises. Atomic durable create without overwriting another
publisher (write+fsync temporary file then exclusive publication), clean own temps.
read_evidence binds all four supplied identities and checksum before use.

Structure summary exact keys:
revision='catalog-structure-evidence-summary-v1', feature_id, predicted_count,
tested_count, located_exact, coordinate_difference, no_location, errors,
untested_count, grouped_command, verifier_game_build_id, generated_count=null,
exhaustive_count=null.
All counts integers>=0. predicted_count=total_count or len(unique predictions),
total_count cannot be smaller than supplied unique predictions. Only checks whose
predicted point belongs to supplied predictions contribute; truncated inputs are
conservative. tested_count is the sum of four check outcome counts;
untested_count=predicted_count-tested_count. Missing payload gives all untested,
verifier_game_build_id=null. grouped_command true for four temple subtypes.
Summary uses passed already-scoped predictions; caller owns square/circle geometry.
No universal accuracy rate or complete game census inferred from all tested starts.

## Codex integration ownership

Codex owns service.py, optional offline importer scripts/catalog_evidence.py,
serving/UI integration, types/contracts and final tests. Product API adds optional
per-row structure_evidence from the overlay, bound to the requested snapshot and
observation_ref, scoped to preview witnesses. Original predicted-count ranking
remains explicit. No source generation at request time. Detail adds per-feature
summaries for the same selected anchor/border; existing raw-read request can validate
against observation. Missing overlay is untested; corrupt overlay returns503.

Frontend shared EvidenceSummary component uses the exact summary fields above.
Show BDS location matches, unresolved tested predictions and untested count. Grouped
temple checks identify generic temple locations only. Show original predicted count,
selected scope and BDS build. Never call partially tested values actual/exhaustive
counts. Keep unqualified presets/records gated. Original Sweep process/native
binaries preserved; only owned Catalog preview may restart after successful checks.
Browser visual/keyboard QA remains deferred by user.

## Required verification

Evidence unit tests for wrong seed/hash/build/source, unsupported feature/command,
invalid/out-of-source/duplicate positions, partial counts and truncated lists,
checksum corruption/missing/oversize/symlink/immutable/racing publication. API tests
with same-anchor radius/border-edge scopes, missing and corrupt overlays and pinned
snapshot identity; no source scan/extraction during preview request. UI render tests
for complete/partial/missing/grouped evidence and user-visible same-scope labels.
Run relevant catalog Python suite, TypeScript/build and existing UI contracts.
