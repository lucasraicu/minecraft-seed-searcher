# Private Catalog pilot

Catalog is a separate tab in the existing Sweep React app. It uses its own
segmented SQLite database and immutable compressed artifacts. Personal search
and public-catalog retention remain separate branches. Catalog HTTP queries never
start seed extraction or modify the personal search database.

The pilot supports eight editable category presets, Required/Preferred structure
counts and positive biome-witness alternatives, three border sides (2048, 4096,
8192 blocks), Recommended settlement, advanced Origin and separately labeled
estimated/game-observed world spawn where the pinned generation has evidence. Every requirement
matches the same saved center. Recommended settlement chooses among 81 saved
centers; it does not find the optimum over every block. Origin means (0,0), not
spawn. Current accuracy generation adds200 estimated and3 game-observed anchors,
with609 border summaries. First-player landing and ground/safety remain gated.
See [practical accuracy contracts](ACCURACY.md).

The Catalog now also has distinct Realm/Server, Presets, Personalized Selection
and Rare Seeds entries. The eight editable category presets belong to Personalized;
the sixteen fixed Sweet16 product cards have their own evidence gates. Five
Origin-circle research leaderboards are derived from existing observations. New
native scans can opt in to independent CPU harvesting with an explicit drain.
See [four-pillar usage and recovery](FOUR_PILLARS_AND_HARVEST.md).

## Open the private preview

Keep an existing Sweep server on port3000 running. Start the Catalog-only backend
and Vite in separate terminals from the project directory:

```sh
PYTHONPATH=src .venv/bin/python -m seed_search.catalog.http_server \
  --root /path/to/segmented/catalog --port 3001
npm --prefix web-ui run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open <http://127.0.0.1:5173/#catalog>. Catalog requests go to3001; existing Sweep
requests go to3000. Opening Catalog directly does not initialize Sweep. Switching
tabs preserves the mounted Sweep workspace. The preview does not replace the
existing `web-ui/dist` or restart the live server.

The current local validation corpus is outside Git at
`~/.local/share/antigravity-worker-mcp/private-pilot-indexed-import-20261020/catalog`.
Shared detail links pin snapshot, world and layout IDs. They work only where that
exact corpus is available; this loopback preview is not a publicly hosted site.

## Saved data and serving

World observations store structure-start coordinates, sampled biome coordinates,
coverage and source identities once per observation. Layout summaries reference
those observations for each center and border. Leaf manifests contain at most256
summaries and1MiB uncompressed; bounded internal manifests reference leaves.
SQLite atomically publishes generations after artifacts are durable. Appends
preserve old generations, so existing queries and cursors remain pinned.

Each leaf binds a rebuildable bitmap index to ordered summary payload hashes and
policy/registry revisions. Required filters select candidate rows before decoding.
Exact scoring selects each world's best eligible layout, then the global Top1000.
Pages contain1–50 unique worlds. Responses report truncation if more than1000
worlds qualify. HMAC cursors bind the exact rank tuple, request, page size and
snapshot, expire after one hour, and do not survive a backend restart unless the
same secret is deliberately supplied by an embedding application.

Serving allows two active requests and two queued admissions. The provisional
query allowance is10seconds; timeout returns an explicit error instead of partial
rankings. An optional bounded cache holds up to eight exact query results for one
hour, with immutable serialized entries. The default64MiB serialized cache budget
is split between results and fallback indexes; Python runtime overhead is separate.
A cache miss reranks the same immutable generation exactly.

Read-only inspection and verified import commands:

```sh
PYTHONPATH=src .venv/bin/python scripts/catalog_pilot.py snapshots --root /path/to/catalog
PYTHONPATH=src .venv/bin/python scripts/catalog_pilot.py audit --root /path/to/catalog
PYTHONPATH=src .venv/bin/python scripts/catalog_pilot.py backup \
  --root /path/to/catalog --destination /path/to/fresh-backup
PYTHONPATH=src .venv/bin/python scripts/catalog_pilot.py import-v1 \
  --source /path/to/legacy-catalog --root /path/to/separate-pilot
```

The legacy bridge is limited to200 source worlds and still loads its old manifest
as a unit. Publication also keeps generation membership metadata in memory. These
are measured pilot limits, not a million-world ingestion architecture. Backups
preserve all generations and registered artifacts; automatic garbage collection
and destructive eviction are not implemented.

## Favorites and participant feedback

Favorites are saved on this browser/device. Export/import and deletion are local;
there are no accounts or cloud synchronization. Signed64 seeds stay decimal
strings throughout JavaScript, URLs, JSON and copying.

Export offers a rich query-feedback file and a separate participant-request file.
For the latter, provide a pseudonym and explicitly identify player, developer or
synthetic provenance. No export is sent automatically. Validate a request array
and prepare disjoint participant groups with:

```sh
PYTHONPATH=src .venv/bin/python scripts/catalog_pilot.py import-requests \
  --input /path/to/catalog-participant-request.json --source player
```

Combine multiple exported arrays into one JSON array before importing. Imports
accept at most1000 requests/1MiB. At least five independently supplied participant
groups are needed for a held-out split. Pseudonym/source declarations are not
independent authentication or proof of player demand. Delete exported files when
no longer needed; the application sends no telemetry and retains no server corpus.

## Evidence and release gates

The catalog is explicitly labeled `research:26.50`. Structure points are predicted
starts, not generated structures or complete bounding boxes. Base biomes are positive
Y63/stride64 witnesses. Additive dense tiles can establish presence or absence only
inside their explicitly covered provider/height/scope. Missing coverage
is unknown, never a completed zero. Limited BDS1.26.52.3 surface observations use
their observed Y and retain separate provenance. They do not certify this entire
model, all23 features, world spawn, terrain or public build compatibility.

Interactive browser QA was explicitly waived by the user. Frontend build,
source-based hook/render/contract checks and reconciled Gemini High reviews pass;
these are not interactive visual checks. Real participant usefulness, broader
generated-structure evidence and public hosting remain separate gates. Public capability
flags and billing remain disabled. This milestone adds no GPU path, custom durable
database engine, payment system, account service or production capacity guarantee.

Larger synthetic validation used500 worlds/121500 layouts with exact query and
retention-oracle parity; full200-world publication survived real killed writers.
The500-world default10-second HTTP capacity gate failed: two admitted cold requests
timed out under eight simultaneous requests, with six explicit busy responses.
This measured bottleneck remains a prerequisite for production scaling.
