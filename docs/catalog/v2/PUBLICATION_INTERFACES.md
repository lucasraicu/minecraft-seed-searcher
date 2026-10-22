# Worker D: additive artifact publication and safe orphan cleanup

Approved plan. High reasoning. Own only src/seed_search/catalog/store.py and
tests/catalog/test_automation_store.py. APPEND AutomationStore; preserve old
CatalogStore semantics. Use existing ArtifactStore and atomic_json/verify_no_symlinks.
No RunCommand/shell/terminal: bridge runs declared checks automatically. Read/edit
builtin tools only. No seed/native/server/BDS/network/build/agents/notification.

Append class AutomationStore(root), objects at root/automation/objects using
ArtifactStore(max_bytes=64<<20); immutable snapshot bindings at
root/automation/snapshots/<64hex>.json and root/automation/current.json. Strict
finiteJSON/boundedbindings, SHA content identity, no symlinks/traversal, no personal
DB reuse. Do not initialize/use pilot.sqlite/catalog.sqlite for this v2 namespace.
Use existing models.world_id(identity) to bind observation/receipt/world.

`stage(observation, summaries)` validates v2 observation (lazyimport), checks each
summary world_id/seed/source_observation_id matches observation and unique layoutIDs;
stores JSONbundle {revision:'catalog-world-bundle-v2',observation,summaries} via CAS;
returns artifact reference (existingArtifactStoremanifest schema). No pointer update.

`publish(ledger, *, fault=None)` where ledger exposes immutable policy_revision,
generation(), population(), retained_worlds(), members(), receipt(world_id).
members entries {objective_id,world_id,rank,member}. receipts contain world_id,
identity,observation_id,artifact,evaluations,replay. Artifact from stage. Build
manifest exactfields {revision:'catalog-snapshot-v2',policy_revision,generation,
population_worlds,worlds:[{world_id,identity,observation_id,artifact}],memberships:list}.
Only winning worlds in manifest, receipts may retain losers. Validate every source
artifact/worldID/observationdigest before publishing; no missing winners silently
skipped. Store manifest in sameCAS, snapshot_id=digest(manifest). Binding exact
{revision:'catalog-snapshot-binding-v2',snapshot_id,generation,artifact}.
Write immutable binding then atomiccurrent pointer, fsync viaexistinghelpers.
If current samecontentreturnexistingid. Call fault('after_manifest') afterbinding
but beforecurrent, fault('after_pointer') aftercurrent; tests actualfailure/replay.
Does NOT ackjob/changeledger. Caller holds queue.publication ownership; no long
transaction needs artifacts inside it. Crashrecovery calls publish(ledger) again.

`snapshots()` verifies allbindings -> list {snapshot_id,generation,worlds,population_worlds}.
`snapshot(snapshot_id=None)` reads binding currentorid and validates CAS/digest and
manifest schema/worldrefs/membershipbinding. Strict unknownfields, boundedfile sizes;
must not write or create a root duringread ifunconfigured (callerhandlesmissing).
`world(snapshot_id,world_id)` verifies membership in requestedsnapshot before
loading sourcebundle, validates identity/observation hash and source summarybinding;
returns bundle. Do not silently return currentworldforhistoricalsnapshot.

`cleanup(ledger, *, mode='dry_run')`: caller holds queue.ownership; validateprotected
roots FIRST. Keep allhistorical published snapshotmanifest artifacts AND theirworld
artifacts, plus ledger.retained_worlds receipts and any receipt with replay.resumable
true (use ledger.receipts() ifneeded; Codex can addmethodafterintegration). If method
unavailable protect every evaluationartifact conservatively, document this.
No changing oldpublishedsnapshots, accuracyfiles, personal DB or legacystorage.
dry_run lists unreachable opaque *.json.gz keys/bytes withoutmutation. quarantine
moves ONLYunreachable to automation/quarantine withsameopaque keys. delete verifies
reachability again and removes onlyalreadyquarantined unreachable artifacts.
Any malformed metadata/symlink/reference/corruption FAILS CLOSED with no moves.
Return {mode,candidates:[relative_key...],bytes,...}; no auto-delete on rankloss.
Publication protects winners BEFORE cleanup; snapshots allimmutable => cursors and
shares remain protected without inventing expiry. Tests independent fakeledger,
actual tempCAS, replaybefore/afterpointer, corruptmanifestfailclosed, missingwinner,
sharedobjects, oldsnapshots, loserquarantine/delete and forbiddenpath checks.
