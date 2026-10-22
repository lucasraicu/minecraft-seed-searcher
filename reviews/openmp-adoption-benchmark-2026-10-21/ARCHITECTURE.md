# Four pillars, bounded rankings and durable data

One public extraction supplies shared records for four views. Realm/Server Seeds
applies server requirements/evidence gates. Presets applies fixed feature/distance
combinations. Personalized Selection ranks the player's required/preferred
filters at one consistent anchor and chosen border. Rare Seeds uses specialist
rankings; currently five research density previews work, while broader promised
records and certification-dependent products remain explicitly gated.

The personal scan and public sample share the declared seed sequence, not personal
qualification. The opt-in CLI handoff records an independent bounded cohort before
personal gates. The current Sweep UI launch command does not automatically turn
on harvesting; an explicit catalog root enables handoff, and a separate bounded
drain performs extraction. Idle catalog serving queries saved data without mining
new seeds. No live harvest was enabled by the server restart.

## Rankings and when data is saved

Personal search maintains its in-memory Top50, deduplicated by seed, with the
worst retained candidate at the heap root. A better candidate can replace it;
when full, the score cutoff can help prune candidates that cannot improve the
personal leaderboard. That personal cutoff is never public admission policy.

Completed personal batches are committed to `realm.sqlite` throughout the run.
The Top50 is updated from committed candidates, periodically saved to JSON/SQLite
and flushed at completion. Restart recovers the heap from durable candidate data.
Compact retention saves qualifying candidates/configured near misses and range
receipts/counters for rejected inputs, not full observations for every rejection.

Public retention has6,931 bounded TopK objectives across structure counts,
structure proximity, biome proximity, biome/landmark combinations, scoring
profiles, diversity buckets and a deterministic reference sample. It preserves
the union of winners, plus pins, with deterministic ties. The current reference
implementation uses sorted bounded lists. This is an explicit selection operation
over catalog data; there are not6,931 continuously running heaps attached to every
personal scan. Ingestion publishes sampled complete records; retention does not
automatically erase previous immutable snapshots. Fine-grained query-time TopK
selection is separate from deciding which worlds to retain.

Public extraction persists checksummed partial checkpoints by feature/biome batch.
Successful complete observations and derived summaries publish as immutable,
content-addressed snapshots. Queue leases/generations and atomic publication
allow restart/replay without inventing complete zero counts or duplicate worlds.
Saving does not wait until the whole campaign ends. Every possible future
preference combination cannot be guaranteed by a finite retained catalog.

## Data and coordinates

The observation layer stores canonical seed/build identity, predicted structure
type/XZ coordinates, sampled biome XYZ/IDs/names, coverage, methods, errors and
measurement metadata. Accuracy/evidence bundles separately record available
estimated/observed world-spawn roles, refined biome tiles and game observations.
They do not certify exact first-player landing or a whole-world physical census.

The base envelope is one shared world-coordinate region. An observation is stored
once rather than duplicated for every border or anchor. Base summaries use
81grid anchors times2048/4096/8192 borders =243layouts/world. Available spawn
roles add their own summaries. Each layout carries counts for near256/512/1024
and inside-border scopes, nearest distances, witness references and completeness.
Recommended settlement chooses the best supported anchor for the actual request;
all conditions must hold at that same anchor. Unknown/out-of-envelope coverage
stays unknown. The base biome plane is sparse Y63/stride64; it is not every block
or every cave height. Extra validated tile/height evidence has explicit scope.

Personal storage: `runs/<run>/realm.sqlite` and recoverable `top50.json`.
Current public root:
`~/.local/share/antigravity-worker-mcp/private-pilot-indexed-import-20261020/catalog/`.
Its `pilot.sqlite` stores metadata, membership and snapshot pointers; checksummed
artifact files store compressed observations, packed summaries and indexes.
`harvest.sqlite` tracks independent public jobs, campaigns and recovery. These
roots are separate; the public store is not a copy of the personal survivor list.
No custom database engine/GPU extraction is active.
