# Approved conditional treasure activation: integration design

Actual controls: CONTROL_RESULTS.json. Four distinct saved worlds, stable API2.10,
pinned BDS1.26.52.3, zero players, signed seed exact, actual locate matches starts,
save confirmation/clean shutdown/owned removal. Two treasure cases have unopened
treasure loot tables and magma-cube spawners; two non-treasure cases have unique
hoglin-stable/bridge loot tables. Shared bastion_other is excluded. Igloo has zero
usable labels and remains unavailable. Unknowns/failures are preserved.

Source catalog-corrected snapshot9637bc21753fa249775f0b11e84ec7a9a92d3872d7982f8e3dfd9a2be4859421
contains all222world observations and V3 summaries. Existing summarize_v3 computes
numeric structure feature blocks even for unavailable features; availability is a
query/retention gate. Therefore reuse source-bound numeric rows rather than run
native extraction or recompute any other features. Independently oracle-check all
treasure counts, nearest witness and completeness against saved subtype2 points
intersected with parent bastion starts, exact half-open Nether windows/radii, and
both inventory/parent coverage. Reject any mismatch rather than silently correcting.

Create a disjoint successor root. Copy immutable history with existing copy_history
(artifacts, accuracy, evidence, product previews, snapshots/generations/pins, pilot
SQLite backup); exclude old mutable harvest/config/current. Configure fresh paused
automation from same identity/options and a snapshot registry differing ONLY in
bastion_treasure available=true and empty unavailable reason. Keep default registry
and legacy JSON contracts unchanged. No gate change for igloo.

Every world bundle gets that new registry. Its rows retain exact feature values,
anchors, dimensions, original observations, legacy payloads, sampling/extension IDs.
Rebind registry_revision and layout_id by existing summarize_v3 formula:
digest(['catalog-summary-v3', observation_id, source_extension_id,
sampling_profile_revision, new_registry_digest, anchor, anchor_modes, border_side]).
Maintain per-world old->new V3 layout map. Rebind packed V5 projections' IDs,
registry and new bundle SHA; validate bindings and rows before publication.

Keep every old objective/world/rank and member value, except rebind a member's
layout_id only when it is in that world's exact V3 map. Embedded legacy layout IDs
remain unchanged. Build ONLY three new enabled treasure near-objective candidate
lists from every saved world, with the existing rank formula and modes: origin,
recommended, and compatible estimated spawn; fixed side2048 for all Nether lists.
Keep best anchor per world, rank and retain2K=40 distinct worlds/objective. Preserve
all nine gated igloo lists empty. Independently compare all7540 other memberships
and the three complete-world treasure oracles before adopting.

Copy all saved receipt evaluations unchanged into the fresh ledger, recording
activation provenance in replay metadata; source receipts and original Realm facts
remain untouched. Publish one complete new manifest only after all222 worlds,
query projections, receipts and merged memberships validate. Frozen historical
snapshots remain readable under their original registry/policy/layout IDs.

New separate rebuild allocation <=600seconds cumulative elapsed, <=4GiB aggregate
process RSS, <=2GiB total successor output including copied history/temp files.
Preflight bytes/free space before copying; durable charge-before-work with elapsed
reconciliation, conservative reservations on interruption. Stop without publishing
on exhaustion. No budget reset; no source/native/game extraction. Validate source
snapshot pin and historical/native/personal preservation. No automatic campaigns.

After focused regressions, all-row oracle/binding audit and successor HTTP/query/
frontend decoder checks (query <=10s), adopt successor public service only. Preserve
personal process91321 and Vite17880. The old root remains rollback/history evidence.
Organization physical batches are independently approval-gated; no concurrent source
moves while variant integration writes are active.
