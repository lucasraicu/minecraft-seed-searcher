"""Isolated catalog store managing SQLite metadata and durable CAS artifacts."""
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import re
import sqlite3
import threading

from .artifacts import ArtifactStore
from . import codec
from . import geometry
from . import models
from . import registry

class _PackedFeatures(Mapping):
    """Decode trusted immutable feature blocks only when the query needs them."""
    def __init__(self, blocks, slots):
        self.blocks=blocks;self.slots=slots;self.decoded={}

    def __len__(self):return len(self.slots)

    def __iter__(self):return iter(self.slots)

    def __getitem__(self,key):
        if key not in self.decoded:
            index,feature=self.slots[key];block=self.blocks[index]
            if not isinstance(block,list) or len(block)!=4:raise ValueError('Invalid packed feature block')
            counts,complete,distance,witness=block
            if feature['kind']=='biome_witness':
                if type(counts)is not int or not 0<=counts<=15:raise ValueError('Invalid packed biome mask')
                counts=[int(bool(counts&(1<<i))) for i in range(4)]
            elif not isinstance(counts,list) or len(counts)!=4:raise ValueError('Invalid packed structure counts')
            if type(complete)is not int or not 0<=complete<=15:raise ValueError('Invalid packed completeness mask')
            if (witness is None)!=(distance is None):raise ValueError('Incomplete packed witness')
            self.decoded[key]=dict(dimension=feature['dimension'],counts=counts,complete=[bool(complete&(1<<i)) for i in range(4)],nearest_d2=distance,witness=witness)
        return self.decoded[key]


_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_PERSONAL_FILES = (
    "seeds.db",
    "personal.db",
    "seed_search.db",
    "runs.db",
    "world_search.db",
    "evaluations.db",
)
_FORBIDDEN_PERSONAL_TABLES = {
    "personal_policy",
    "evaluations",
    "seed_candidates",
    "runs",
    "search_runs",
}
SCHEMA_REVISION = "catalog-reference-v1"


class CatalogStore:
    """Catalog metadata and artifact coordinator with atomic snapshot publication and safe restore."""

    def __init__(self, root: str | Path, max_artifact_bytes: int = 16 * 1024 * 1024):
        if not root:
            raise ValueError("Root directory must be provided")

        raw_path = Path(root)
        if raw_path.is_symlink():
            raise ValueError(f"Root path cannot be a symlink: {root}")
        self.root = raw_path.resolve()
        if raw_path.is_symlink() or self.root.is_symlink():
            raise ValueError(f"Root path cannot be a symlink: {root}")

        # Enforce exclusively new catalog root; reject personal DB reuse
        for forbidden in _FORBIDDEN_PERSONAL_FILES:
            if (self.root / forbidden).exists():
                raise ValueError(f"Personal database file {forbidden} detected in root; reuse prohibited")

        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink() or raw_path.is_symlink():
            raise ValueError(f"Root path cannot be a symlink: {root}")

        self.db_path = self.root / "catalog.sqlite"
        for name in ('catalog.sqlite', 'catalog.sqlite-wal', 'catalog.sqlite-shm'):
            if (self.root / name).is_symlink():
                raise ValueError('Symlink database files are not allowed')
        if self.db_path.exists():
            # Check ownership before any journal-mode pragma can modify the file.
            try:
                with sqlite3.connect(self.db_path.as_uri() + '?mode=ro', uri=True) as probe:
                    tables = {row[0] for row in probe.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if tables & _FORBIDDEN_PERSONAL_TABLES:
                        raise ValueError('Personal database schema detected; reuse prohibited')
                    if 'schema_meta' not in tables:
                        raise ValueError('Incompatible database: missing schema_meta marker')
                    rows = probe.execute('SELECT revision, status FROM schema_meta').fetchall()
                    if rows != [(SCHEMA_REVISION, 'active')]:
                        raise ValueError('Incompatible catalog schema marker')
            except sqlite3.Error as error:
                raise ValueError('Not an existing reference catalog database') from error
        self.artifacts = ArtifactStore(self.root / "artifacts", max_bytes=max_artifact_bytes)
        self._lock = threading.RLock()
        self.conn = None
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0,
            isolation_level=None  # Explicit transaction management
        )
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = FULL;")

        cursor = conn.cursor()
        existing_tables = {
            r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        }

        # Check for forbidden personal DB tables
        if existing_tables & _FORBIDDEN_PERSONAL_TABLES:
            conn.close()
            raise ValueError("Personal database schema detected in catalog database; reuse prohibited")

        if existing_tables:
            # Existing database must have explicit schema marker
            if "schema_meta" not in existing_tables:
                conn.close()
                raise ValueError("Incompatible database: missing schema_meta marker")

            rows = cursor.execute("SELECT revision, status FROM schema_meta;").fetchall()
            if not rows or rows[0][0] != SCHEMA_REVISION:
                conn.close()
                raise ValueError(f"Incompatible database schema revision: {rows}")
        else:
            # Create fresh catalog schema
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                cursor.execute("""
                    CREATE TABLE schema_meta (
                        revision TEXT PRIMARY KEY,
                        status TEXT NOT NULL
                    );
                """)
                cursor.execute("INSERT INTO schema_meta VALUES (?, 'active');", (SCHEMA_REVISION,))

                cursor.execute("""
                    CREATE TABLE artifact (
                        sha256 TEXT PRIMARY KEY CHECK (length(sha256)=64),
                        relative_key TEXT NOT NULL UNIQUE,
                        byte_length INTEGER NOT NULL CHECK (byte_length>=0),
                        uncompressed_length INTEGER NOT NULL CHECK (uncompressed_length>=0),
                        codec TEXT NOT NULL,
                        published_at TEXT NOT NULL
                    );
                """)

                cursor.execute("""
                    CREATE TABLE observation_set (
                        observation_id TEXT PRIMARY KEY CHECK (length(observation_id)=64),
                        world_id TEXT NOT NULL CHECK (length(world_id)=64),
                        seed TEXT NOT NULL,
                        manifest_sha256 TEXT NOT NULL REFERENCES artifact(sha256),
                        created_at TEXT NOT NULL
                    );
                """)

                cursor.execute("""
                    CREATE TABLE layout (
                        layout_id TEXT PRIMARY KEY CHECK (length(layout_id)=64),
                        observation_id TEXT NOT NULL REFERENCES observation_set(observation_id),
                        world_id TEXT NOT NULL CHECK (length(world_id)=64),
                        seed TEXT NOT NULL,
                        anchor_x INTEGER NOT NULL,
                        anchor_z INTEGER NOT NULL,
                        border_side INTEGER NOT NULL,
                        revision TEXT NOT NULL,
                        payload_blob BLOB NOT NULL CHECK (length(payload_blob)=364),
                        blob_sha256 TEXT NOT NULL CHECK (length(blob_sha256)=64),
                        created_at TEXT NOT NULL
                    );
                """)

                cursor.execute("""
                    CREATE TABLE catalog_snapshot (
                        snapshot_id TEXT PRIMARY KEY CHECK (length(snapshot_id)=64),
                        manifest_sha256 TEXT NOT NULL REFERENCES artifact(sha256),
                        registry_revision TEXT NOT NULL,
                        geometry_revision TEXT NOT NULL,
                        published_at TEXT NOT NULL
                    );
                """)

                cursor.execute("""
                    CREATE TABLE snapshot_observation (
                        snapshot_id TEXT NOT NULL REFERENCES catalog_snapshot(snapshot_id) ON DELETE CASCADE,
                        observation_id TEXT NOT NULL REFERENCES observation_set(observation_id),
                        PRIMARY KEY (snapshot_id, observation_id)
                    );
                """)

                cursor.execute("""
                    CREATE TABLE snapshot_layout (
                        snapshot_id TEXT NOT NULL REFERENCES catalog_snapshot(snapshot_id) ON DELETE CASCADE,
                        layout_id TEXT NOT NULL REFERENCES layout(layout_id),
                        PRIMARY KEY (snapshot_id, layout_id)
                    );
                """)

                cursor.execute("CREATE INDEX idx_obs_world ON observation_set(world_id);")
                cursor.execute("CREATE INDEX idx_layout_obs ON layout(observation_id);")
                cursor.execute("CREATE INDEX idx_layout_world ON layout(world_id);")
                cursor.execute("CREATE INDEX idx_snap_obs ON snapshot_observation(snapshot_id);")
                cursor.execute("CREATE INDEX idx_snap_layout ON snapshot_layout(snapshot_id);")
                cursor.execute("COMMIT;")
            except Exception:
                cursor.execute("ROLLBACK;")
                conn.close()
                raise

        self.conn = conn

    def _check_open(self) -> None:
        if self.conn is None:
            raise RuntimeError("CatalogStore is closed")

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            if self.conn is not None:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None

    def __enter__(self) -> "CatalogStore":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def publish_snapshot(self, observations: list[dict], layouts: list[dict]) -> str:
        """Atomically publish observations and layouts into a content-addressed snapshot."""
        self._check_open()

        if not isinstance(observations, list) or not isinstance(layouts, list):
            raise ValueError("Observations and layouts must be lists")
        if not observations:
            raise ValueError("Cannot publish snapshot with zero observations")
        if not layouts:
            raise ValueError("Cannot publish snapshot with zero layouts")

        # Validate observations and prevent intra-batch duplicate/conflicts
        obs_by_id = {}
        world_ids = set()
        build_headers = set()
        for obs in observations:
            models.validate_observation(obs)
            oid = models.observation_id(obs)
            if oid in obs_by_id:
                raise ValueError(f"Duplicate observation in publication batch: {oid}")
            wid = models.world_id(obs['identity'])
            if wid in world_ids:
                raise ValueError('Only one observation per world is allowed in a reference snapshot')
            world_ids.add(wid)
            build_headers.add(tuple((k,v) for k,v in sorted(obs['identity'].items()) if k != 'seed'))
            obs_by_id[oid] = obs
        if len(build_headers) != 1:
            raise ValueError('Mixed build/settings identities in reference snapshot')

        # Validate layouts and prevent intra-batch duplicate/conflicts
        layouts_by_id = {}
        layout_blobs = {}
        layout_blob_hashes = {}
        for summary in layouts:
            codec.validate_summary(summary)
            lid = summary["layout_id"]
            if lid in layouts_by_id:
                raise ValueError(f"Duplicate layout in publication batch: {lid}")

            oid = summary["observation_id"]
            if oid not in obs_by_id:
                raise ValueError(f"Layout {lid} references observation_id {oid} not in supplied observations")

            obs = obs_by_id[oid]
            if summary["world_id"] != models.world_id(obs["identity"]):
                raise ValueError(f"Layout {lid} world_id does not match observation world_id")
            if summary["seed"] != obs["identity"]["seed"]:
                raise ValueError(f"Layout {lid} seed does not match observation seed")
            if tuple(summary["anchor"]) not in geometry.anchors():
                raise ValueError(f"Layout {lid} has unsupported anchor {summary['anchor']}")
            if summary["border_side"] not in registry.SIDES:
                raise ValueError(f"Layout {lid} has unsupported border_side {summary['border_side']}")

            blob = codec.pack_summary(summary)
            if len(blob) != 364:
                raise ValueError(f"Packed summary payload must be 364 bytes, got {len(blob)}")
            bhash = hashlib.sha256(blob).hexdigest()

            layouts_by_id[lid] = summary
            layout_blobs[lid] = blob
            layout_blob_hashes[lid] = bhash

        # Check for immutability conflicts against existing store records
        obs_existing_manifests = {}
        with self._lock:
            cur = self.conn.cursor()
            for oid, obs in obs_by_id.items():
                cur.execute("SELECT manifest_sha256 FROM observation_set WHERE observation_id = ?;", (oid,))
                row = cur.fetchone()
                if row:
                    cur.execute(
                        "SELECT sha256, relative_key, byte_length, uncompressed_length, codec FROM artifact WHERE sha256 = ?;",
                        (row[0],)
                    )
                    m_row = cur.fetchone()
                    if not m_row:
                        raise ValueError(f"Corrupt database: missing artifact record for observation {oid}")
                    existing_m = {
                        "sha256": m_row[0],
                        "relative_key": m_row[1],
                        "byte_length": m_row[2],
                        "uncompressed_length": m_row[3],
                        "codec": m_row[4],
                    }
                    existing_obs = self.artifacts.get_json(existing_m)
                    if existing_obs != obs:
                        raise ValueError(f"Conflict: observation {oid} already exists with different data (immutable)")
                    obs_existing_manifests[oid] = existing_m

            for lid in layouts_by_id:
                cur.execute("SELECT payload_blob, blob_sha256 FROM layout WHERE layout_id = ?;", (lid,))
                l_row = cur.fetchone()
                if l_row:
                    if l_row[0] != layout_blobs[lid] or l_row[1] != layout_blob_hashes[lid]:
                        raise ValueError(f"Conflict: layout {lid} already exists with different blob (immutable)")

            # Stable content-address snapshot identity
            sorted_obs_ids = sorted(obs_by_id.keys())
            sorted_layout_ids = sorted(layouts_by_id.keys())
            snapshot_descriptor = {
                "geometry_revision": models.GEOMETRY_REVISION,
                "layout_digests": sorted_layout_ids,
                "layout_payload_sha256": dict(sorted(layout_blob_hashes.items())),
                "observation_digests": sorted_obs_ids,
                "registry_revision": registry.REGISTRY_REVISION,
                "summary_revision": models.SUMMARY_REVISION,
                "score_revision": registry.POLICY['score']['revision'],
                "policy_sha256": registry.digest(registry.POLICY),
            }
            snapshot_id = registry.digest(snapshot_descriptor)

            # Check if this snapshot is already published (idempotent replay)
            cur.execute("SELECT snapshot_id FROM catalog_snapshot WHERE snapshot_id = ?;", (snapshot_id,))
            if cur.fetchone():
                self.snapshot(snapshot_id)  # A corrupt publication is not success on replay.
                return snapshot_id

        # DURABILITY FIRST: write artifacts to durable storage BEFORE database transaction
        obs_manifests = {}
        for oid, obs in obs_by_id.items():
            if oid in obs_existing_manifests:
                obs_manifests[oid] = obs_existing_manifests[oid]
            else:
                obs_manifests[oid] = self.artifacts.put_json(obs)

        snapshot_manifest_payload = dict(snapshot_descriptor, snapshot_id=snapshot_id)
        snap_manifest = self.artifacts.put_json(snapshot_manifest_payload)

        # Single atomic metadata transaction
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                # Insert artifact records
                for m in obs_manifests.values():
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO artifact
                        (sha256, relative_key, byte_length, uncompressed_length, codec, published_at)
                        VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (m["sha256"], m["relative_key"], m["byte_length"], m["uncompressed_length"], m["codec"], now)
                    )

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO artifact
                    (sha256, relative_key, byte_length, uncompressed_length, codec, published_at)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        snap_manifest["sha256"],
                        snap_manifest["relative_key"],
                        snap_manifest["byte_length"],
                        snap_manifest["uncompressed_length"],
                        snap_manifest["codec"],
                        now
                    )
                )

                # Insert observation records
                for oid, obs in obs_by_id.items():
                    wid = models.world_id(obs["identity"])
                    seed_str = obs["identity"]["seed"]
                    m = obs_manifests[oid]
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO observation_set
                        (observation_id, world_id, seed, manifest_sha256, created_at)
                        VALUES (?, ?, ?, ?, ?);
                        """,
                        (oid, wid, seed_str, m["sha256"], now)
                    )

                # Insert layout records
                for lid, summary in layouts_by_id.items():
                    blob = layout_blobs[lid]
                    bhash = layout_blob_hashes[lid]
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO layout
                        (layout_id, observation_id, world_id, seed, anchor_x, anchor_z,
                         border_side, revision, payload_blob, blob_sha256, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            lid,
                            summary["observation_id"],
                            summary["world_id"],
                            summary["seed"],
                            summary["anchor"][0],
                            summary["anchor"][1],
                            summary["border_side"],
                            summary["revision"],
                            blob,
                            bhash,
                            now
                        )
                    )

                # Insert snapshot record
                cursor.execute(
                    """
                    INSERT INTO catalog_snapshot
                    (snapshot_id, manifest_sha256, registry_revision, geometry_revision, published_at)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (snapshot_id, snap_manifest["sha256"], registry.REGISTRY_REVISION, models.GEOMETRY_REVISION, now)
                )

                # Cross-links
                for oid in sorted_obs_ids:
                    cursor.execute(
                        "INSERT INTO snapshot_observation (snapshot_id, observation_id) VALUES (?, ?);",
                        (snapshot_id, oid)
                    )
                for lid in sorted_layout_ids:
                    cursor.execute(
                        "INSERT INTO snapshot_layout (snapshot_id, layout_id) VALUES (?, ?);",
                        (snapshot_id, lid)
                    )

                cursor.execute("COMMIT;")
            except Exception:
                cursor.execute("ROLLBACK;")
                raise

        return snapshot_id

    def snapshot(self, snapshot_id: str) -> dict:
        """Retrieve and comprehensively verify a published snapshot."""
        self._check_open()

        if not isinstance(snapshot_id, str) or not _HEX64_RE.fullmatch(snapshot_id):
            raise KeyError(f"Invalid or unknown snapshot_id: {snapshot_id}")

        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT snapshot_id, manifest_sha256, registry_revision, geometry_revision, published_at
                FROM catalog_snapshot
                WHERE snapshot_id = ?;
                """,
                (snapshot_id,)
            )
            snap_row = cur.fetchone()
            if not snap_row:
                raise KeyError(f"Unknown snapshot: {snapshot_id}")

            if snap_row[2] != registry.REGISTRY_REVISION or snap_row[3] != models.GEOMETRY_REVISION:
                raise ValueError("Incompatible registry or geometry revision in snapshot")

            # Fetch snapshot manifest artifact
            cur.execute(
                """
                SELECT sha256, relative_key, byte_length, uncompressed_length, codec
                FROM artifact
                WHERE sha256 = ?;
                """,
                (snap_row[1],)
            )
            art_row = cur.fetchone()
            if not art_row:
                raise ValueError("Corrupt snapshot: missing snapshot manifest artifact record")

            snap_manifest = {
                "sha256": art_row[0],
                "relative_key": art_row[1],
                "byte_length": art_row[2],
                "uncompressed_length": art_row[3],
                "codec": art_row[4],
            }
            snap_payload = self.artifacts.get_json(snap_manifest)

            # Verify descriptor
            expected_sid = registry.digest({
                "geometry_revision": snap_payload["geometry_revision"],
                "layout_digests": snap_payload["layout_digests"],
                "layout_payload_sha256": snap_payload['layout_payload_sha256'],
                "observation_digests": snap_payload["observation_digests"],
                "registry_revision": snap_payload["registry_revision"],
                "summary_revision": snap_payload['summary_revision'],
                "score_revision": snap_payload['score_revision'],
                "policy_sha256": snap_payload['policy_sha256'],
            })
            if expected_sid != snapshot_id:
                raise ValueError("Snapshot manifest descriptor does not match snapshot_id")
            if (snap_payload['registry_revision'] != registry.REGISTRY_REVISION or
                snap_payload['geometry_revision'] != models.GEOMETRY_REVISION or
                snap_payload['summary_revision'] != models.SUMMARY_REVISION or
                snap_payload['score_revision'] != registry.POLICY['score']['revision']):
                raise ValueError('Incompatible snapshot revisions')
            if snap_payload['policy_sha256'] != registry.digest(registry.POLICY):
                raise ValueError('Snapshot policy content mismatch')

            # Load and verify observations
            cur.execute(
                """
                SELECT o.observation_id, a.sha256, a.relative_key, a.byte_length, a.uncompressed_length, a.codec
                FROM snapshot_observation so
                JOIN observation_set o ON so.observation_id = o.observation_id
                JOIN artifact a ON o.manifest_sha256 = a.sha256
                WHERE so.snapshot_id = ?
                ORDER BY o.observation_id;
                """,
                (snapshot_id,)
            )
            obs_rows = cur.fetchall()
            if len(obs_rows) != len(snap_payload["observation_digests"]):
                raise ValueError("Corrupt snapshot: observation count mismatch")
            if [row[0] for row in obs_rows] != snap_payload['observation_digests']:
                raise ValueError('Snapshot observation membership mismatch')

            observations = []
            obs_by_id = {}
            for row in obs_rows:
                oid, sha, rk, bl, ul, codec_name = row
                m = {
                    "sha256": sha,
                    "relative_key": rk,
                    "byte_length": bl,
                    "uncompressed_length": ul,
                    "codec": codec_name,
                }
                obs = self.artifacts.get_json(m)
                models.validate_observation(obs)
                actual_oid = models.observation_id(obs)
                if actual_oid != oid:
                    raise ValueError(f"Observation ID mismatch: expected {oid}, got {actual_oid}")
                observations.append(obs)
                obs_by_id[oid] = obs

            # Load and verify layouts
            cur.execute(
                """
                SELECT l.layout_id, l.observation_id, l.world_id, l.seed,
                       l.anchor_x, l.anchor_z, l.border_side, l.revision,
                       l.payload_blob, l.blob_sha256
                FROM snapshot_layout sl
                JOIN layout l ON sl.layout_id = l.layout_id
                WHERE sl.snapshot_id = ?
                ORDER BY l.layout_id;
                """,
                (snapshot_id,)
            )
            layout_rows = cur.fetchall()
            if len(layout_rows) != len(snap_payload["layout_digests"]):
                raise ValueError("Corrupt snapshot: layout count mismatch")
            if [row[0] for row in layout_rows] != snap_payload['layout_digests']:
                raise ValueError('Snapshot layout membership mismatch')

            layouts = []
            for row in layout_rows:
                lid, oid, wid, seed, ax, az, side, rev, blob, bhash = row
                if hashlib.sha256(blob).hexdigest() != bhash:
                    raise ValueError(f"Corrupt layout blob checksum for layout {lid}")
                if snap_payload['layout_payload_sha256'].get(lid) != bhash:
                    raise ValueError('Snapshot payload digest mismatch')
                if len(blob) != 364:
                    raise ValueError(f"Corrupt layout blob length != 364 for layout {lid}")

                if oid not in obs_by_id:
                    raise ValueError(f"Layout {lid} references observation {oid} not in snapshot")
                obs = obs_by_id[oid]
                if wid != models.world_id(obs["identity"]):
                    raise ValueError(f"Layout {lid} world_id cross-link mismatch")
                if seed != obs["identity"]["seed"]:
                    raise ValueError(f"Layout {lid} seed cross-link mismatch")

                anchor = [ax, az]
                if tuple(anchor) not in geometry.anchors():
                    raise ValueError(f"Layout {lid} anchor invalid: {anchor}")
                if side not in registry.SIDES:
                    raise ValueError(f"Layout {lid} border_side invalid: {side}")
                if lid != codec.layout_id(oid, anchor, side):
                    raise ValueError(f"Layout {lid} identity mismatch")

                metadata = {
                    "revision": rev,
                    "observation_id": oid,
                    "world_id": wid,
                    "layout_id": lid,
                    "seed": seed,
                    "anchor": anchor,
                    "border_side": side,
                }
                summary = codec.unpack_summary(blob, metadata)
                codec.validate_summary(summary)
                layouts.append(summary)

        return {
            "snapshot_id": snapshot_id,
            "observations": observations,
            "layouts": layouts,
        }

    def backup(self, destination: str | Path) -> None:
        """Create a consistent backup at a fresh destination and verify restored snapshots."""
        self._check_open()

        if not destination:
            raise ValueError("Destination must be provided")

        raw_dest = Path(destination)
        if raw_dest.is_symlink():
            raise ValueError(f"Destination cannot be a symlink: {destination}")
        dest = raw_dest.resolve()
        if raw_dest.is_symlink() or dest.is_symlink():
            raise ValueError(f"Destination cannot be a symlink: {destination}")

        if dest.exists() and any(dest.iterdir()):
            raise ValueError("Destination must be a fresh empty directory")
        dest.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink() or raw_dest.is_symlink():
            raise ValueError(f"Destination cannot be a symlink: {destination}")

        dest_db_path = dest / "catalog.sqlite"
        dest_conn = sqlite3.connect(str(dest_db_path), isolation_level=None)
        try:
            with self._lock:
                self.conn.backup(dest_conn)
        finally:
            dest_conn.close()

        # Copy referenced artifacts safely
        dest_artifacts = ArtifactStore(dest / "artifacts")
        chk = sqlite3.connect(str(dest_db_path))
        try:
            artifacts = chk.execute(
                "SELECT sha256, relative_key, byte_length FROM artifact;"
            ).fetchall()
            snapshot_ids = [
                r[0] for r in chk.execute("SELECT snapshot_id FROM catalog_snapshot;").fetchall()
            ]
        finally:
            chk.close()

        for sha, rk, bl in artifacts:
            self.artifacts.copy_raw_to(rk, dest_artifacts, expected_sha=sha, expected_len=bl)

        # Verify all restored snapshots using safe store API
        with CatalogStore(dest) as restored:
            for sid in snapshot_ids:
                restored.snapshot(sid)


class AutomationStore:
    """Additive immutable v2 bundles/snapshots; caller serializes writers with queue ownership."""
    _PAGE_THRESHOLD_BYTES = 8 * 1024 * 1024
    _PAGE_ITEM_LIMIT = 2048
    _PAGE_BYTE_LIMIT = 4 * 1024 * 1024
    _INDEX_PAGE_LIMIT = 1024

    def __init__(self,root):
        from .ingestion import verify_no_symlinks
        self.root=verify_no_symlinks(Path(root).absolute())
        for name in _FORBIDDEN_PERSONAL_FILES:
            if (self.root/name).exists():raise ValueError('Personal database root prohibited')
        self.base=verify_no_symlinks(self.root/'automation')
        self.objects_dir=self.base/'objects';self.snapshots_dir=self.base/'snapshots'
        self.current_path=self.base/'current.json';self.quarantine_dir=self.base/'quarantine'
        self.generations_dir=self.base/'generations'
        self._artifacts=None
        self._query_validator=None

    @property
    def artifacts(self):
        if self._artifacts is None:self._artifacts=ArtifactStore(self.objects_dir)
        return self._artifacts

    @staticmethod
    def _sha(value):
        if not isinstance(value,str) or not _HEX64_RE.fullmatch(value):raise ValueError('Invalid SHA identity')
        return value

    def _query_validator_id(self):
        if self._query_validator is None:
            import hashlib
            folder=Path(__file__).parent
            self._query_validator=registry.digest([registry.REGISTRY_REVISION_V2,
                {name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in
                 ('codec.py','anchors.py','geometry.py','models.py')}])
        return self._query_validator

    def _read(self,path,*,max_bytes=16384):
        from .ingestion import verify_no_symlinks,strict_json_loads
        path=verify_no_symlinks(path)
        if not path.is_file():raise FileNotFoundError(path)
        if path.stat().st_size>max_bytes:raise ValueError('Metadata byte cap')
        return strict_json_loads(path.read_bytes())

    def _bundle(self,value,entry=None):
        from .models import validate_observation_v2
        from .codec import validate_summary_v2
        v3=isinstance(value,dict) and value.get('revision')=='catalog-world-bundle-v3'
        fields={'revision','observation','summaries'}
        if not isinstance(value,dict) or set(value)!=(fields|{'registry','extension_artifact'} if v3 else fields) or value['revision'] not in ('catalog-world-bundle-v2','catalog-world-bundle-v3'):
            raise ValueError('Invalid world bundle')
        obs=validate_observation_v2(value['observation']);oid=registry.digest(obs);wid=models.world_id(obs['identity'])
        if entry is not None and (entry['world_id']!=wid or entry['identity']!=obs['identity'] or entry['observation_id']!=oid):
            raise ValueError('World bundle source mismatch')
        extension=None
        if v3:
            from .codec import validate_summary_v3
            from .registry import digest
            if not isinstance(value['registry'],dict) or value['registry'].get('revision')!='catalog-features-v3':raise ValueError('Invalid bundle registry')
            if value['extension_artifact'] is not None:
                extension=self.artifacts.get_json(value['extension_artifact'])
                from .biome_extension import validate_extension
                validate_extension(extension,obs)
        rows=value['summaries']
        if not isinstance(rows,list) or len(rows)>1024:raise ValueError('Summary count cap')
        seen=set()
        for row in rows:
            if v3:
                validate_summary_v3(row,registry=value['registry'])
                expected_extension=registry.digest(extension) if extension is not None else None
                if row['source_extension_id']!=expected_extension:raise ValueError('Extension source differs')
                if entry is not None and 'registry_revision' in entry and any(row[k]!=entry[k] for k in ('registry_revision','sampling_profile_revision','source_extension_id')):raise ValueError('V3 snapshot binding differs')
            else:validate_summary_v2(row)
            if row['world_id']!=wid or row['seed']!=obs['identity']['seed'] or row['source_observation_id']!=oid:
                raise ValueError('Summary source mismatch')
            if row['layout_id'] in seen:raise ValueError('Duplicate layout')
            seen.add(row['layout_id'])
        return value

    def stage(self,observation,summaries,*,extension=None,registry_v3=None):
        value=dict(revision='catalog-world-bundle-v2',observation=observation,summaries=summaries)
        if registry_v3 is not None:
            value.update(revision='catalog-world-bundle-v3',registry=registry_v3,
                extension_artifact=self.artifacts.put_json(extension) if extension is not None else None)
        bundle=self._bundle(value)
        return self.artifacts.put_json(bundle)

    def _manifest(self,value):
        from .harvest import _validate_rank
        fields={'revision','policy_revision','generation','population_worlds','worlds','memberships'}
        v3=isinstance(value,dict) and value.get('revision')=='catalog-snapshot-v3'
        if v3:fields|={'policy_contract','registry','sampling_profile_revision','reserve_policy'}
        if not isinstance(value,dict) or set(value) not in (fields,fields|{'product_status'}) or value['revision'] not in ('catalog-snapshot-v2','catalog-snapshot-v3'):raise ValueError('Invalid snapshot schema')
        max_slots=105644;objectives=None
        if v3:
            from .reserve_policy import validate_contract,contract,reserve_metadata
            _,max_slots=validate_contract(value['policy_contract']);objectives=contract()['retained_objectives']
            if value['reserve_policy'] not in (reserve_metadata(),reserve_metadata(historically_complete=True)):raise ValueError('Invalid reserve metadata')
            self._sha(value['sampling_profile_revision'])
            if not isinstance(value['registry'],dict) or value['registry'].get('revision')!='catalog-features-v3':raise ValueError('Invalid snapshot registry')
        self._sha(value['policy_revision'])
        for key in ('generation','population_worlds'):
            if type(value[key]) is not int or value[key]<0:raise ValueError('Invalid snapshot counters')
        if 'product_status' in value and not isinstance(value['product_status'],dict):raise ValueError('Invalid product status totals')
        for pid,counts in value.get('product_status',{}).items():
            if (not isinstance(pid,str) or not isinstance(counts,dict) or set(counts)!={'match','no_match','pending'}
                    or any(type(n) is not int or n<0 for n in counts.values())
                    or sum(counts.values())>value['population_worlds']):raise ValueError('Invalid product status totals')
        worlds=value['worlds'];members=value['memberships']
        if not isinstance(worlds,list) or len(worlds)>max_slots or len(worlds)>value['population_worlds'] or not isinstance(members,list) or len(members)>max_slots:
            raise ValueError('Snapshot capacity exceeded')
        by_world={};headers=set()
        for entry in worlds:
            fields={'world_id','identity','observation_id','artifact'}
            if v3:fields|={'registry_revision','sampling_profile_revision','source_extension_id'}
            if not isinstance(entry,dict) or set(entry) not in (fields,fields|{'summary_artifacts'}):raise ValueError('Invalid world reference')
            if v3:
                if entry['registry_revision']!=registry.digest(value['registry']) or entry['sampling_profile_revision']!=value['sampling_profile_revision']:raise ValueError('Snapshot evidence revision mismatch')
                if entry['source_extension_id'] is not None:self._sha(entry['source_extension_id'])
            wid=self._sha(entry['world_id']);self._sha(entry['observation_id']);models.validate_identity(entry['identity'])
            if wid in by_world or models.world_id(entry['identity'])!=wid:raise ValueError('Duplicate or unbound world')
            self.artifacts._validate_manifest(entry['artifact']);by_world[wid]=entry
            if 'summary_artifacts' in entry:
                if not isinstance(entry['summary_artifacts'],dict) or set(entry['summary_artifacts'])!={'2048','4096','8192'}:
                    raise ValueError('Invalid summary projection scopes')
                for artifact in entry['summary_artifacts'].values():self.artifacts._validate_manifest(artifact)
            headers.add(registry.digest({k:v for k,v in entry['identity'].items() if k!='seed'}))
        if len(headers)>1:raise ValueError('Mixed predictor generations')
        seen=set();previous=None;objective_counts={}
        for row in members:
            if not isinstance(row,dict) or set(row)!={'objective_id','world_id','rank','member'}:raise ValueError('Invalid membership')
            oid=row['objective_id'];wid=row['world_id'];member=row['member']
            if not isinstance(oid,str) or not 1<=len(oid)<=256 or wid not in by_world or not isinstance(member,dict) or member.get('world_id')!=wid:
                raise ValueError('Unbound winning member')
            if v3:
                if oid not in objectives:raise ValueError('Unknown v3objective')
                objective_counts[oid]=objective_counts.get(oid,0)+1
                if objective_counts[oid]>objectives[oid]:raise ValueError('Objective capacity exceeded')
            key=(oid,wid)
            if key in seen:raise ValueError('Duplicate winning membership')
            seen.add(key)
            for field in ('source_observation_id','observation_id'):
                if field in member and member[field]!=by_world[wid]['observation_id']:raise ValueError('Stale member source')
            ordered=(oid,_validate_rank(row['rank']),wid)
            if previous is not None and ordered<previous:raise ValueError('Unordered winning members')
            previous=ordered
        if set(by_world)!={r['world_id'] for r in members}:raise ValueError('Unreferenced snapshot world')
        return value

    def _write_manifest(self,manifest,*,compression_level=9):
        raw=registry.canonical_json(manifest)
        if len(raw)<=getattr(self,'_PAGE_THRESHOLD_BYTES',8*1024*1024):
            return self.artifacts.put_json(manifest,compression_level=compression_level)
        item_limit=getattr(self,'_PAGE_ITEM_LIMIT',2048)
        byte_limit=getattr(self,'_PAGE_BYTE_LIMIT',4*1024*1024)
        pages=[]
        for kind,items in (('worlds',manifest['worlds']),('memberships',manifest['memberships'])):
            if not items:continue
            cur=[];cur_bytes=0
            header_bytes=len(registry.canonical_json(dict(revision='catalog-snapshot-page-v2',kind=kind,count=0,items=[])))
            for item in items:
                item_raw=registry.canonical_json(item)
                item_len=len(item_raw)
                next_bytes=header_bytes+len(str(len(cur)+1))-1+cur_bytes+item_len+len(cur)
                if cur and (len(cur)>=item_limit or next_bytes>byte_limit):
                    page=dict(revision='catalog-snapshot-page-v2',kind=kind,count=len(cur),items=cur)
                    if len(registry.canonical_json(page))>byte_limit:raise ValueError('Page byte cap exceeded')
                    if len(pages)>=self._INDEX_PAGE_LIMIT:raise ValueError('Snapshot index page limit exceeded')
                    page_art=self.artifacts.put_json(page,compression_level=compression_level)
                    pages.append(dict(kind=kind,count=len(cur),artifact=page_art))
                    cur=[item];cur_bytes=len(item_raw)
                else:
                    cur.append(item);cur_bytes+=item_len
            if cur:
                page=dict(revision='catalog-snapshot-page-v2',kind=kind,count=len(cur),items=cur)
                if len(registry.canonical_json(page))>byte_limit:raise ValueError('Page byte cap exceeded')
                if len(pages)>=self._INDEX_PAGE_LIMIT:raise ValueError('Snapshot index page limit exceeded')
                page_art=self.artifacts.put_json(page,compression_level=compression_level)
                pages.append(dict(kind=kind,count=len(cur),artifact=page_art))
        if len(pages)>getattr(self,'_INDEX_PAGE_LIMIT',1024):raise ValueError('Snapshot index page limit exceeded')
        index=dict(
            revision='catalog-snapshot-index-v2',
            policy_revision=manifest['policy_revision'],
            generation=manifest['generation'],
            population_worlds=manifest['population_worlds'],
            pages=pages,
        )
        if manifest['revision']=='catalog-snapshot-v3':
            index['revision']='catalog-snapshot-index-v3'
            index.update({k:manifest[k] for k in ('policy_contract','registry','sampling_profile_revision','reserve_policy')})
        if 'product_status' in manifest:index['product_status']=manifest['product_status']
        if len(registry.canonical_json(index))>16*1024*1024:raise ValueError('Index size cap exceeded')
        return self.artifacts.put_json(index,compression_level=compression_level)

    def _resolve_manifest(self,artifact,protected=None):
        self.artifacts._validate_manifest(artifact)
        if protected is not None:protected.add(artifact['relative_key'])
        payload=self.artifacts.get_json(artifact)
        if not isinstance(payload,dict):raise ValueError('Invalid artifact payload')
        rev=payload.get('revision')
        if rev in ('catalog-snapshot-v2','catalog-snapshot-v3'):return self._manifest(payload)
        if rev not in ('catalog-snapshot-index-v2','catalog-snapshot-index-v3'):raise ValueError('Unknown manifest revision')
        v3=rev=='catalog-snapshot-index-v3';max_slots=105644
        fields={'revision','policy_revision','generation','population_worlds','pages'}
        if v3:
            fields|={'policy_contract','registry','sampling_profile_revision','reserve_policy'}
            from .reserve_policy import validate_contract
            _,max_slots=validate_contract(payload.get('policy_contract'))
        if set(payload) not in (fields,fields|{'product_status'}):
            raise ValueError('Invalid snapshot index schema')
        self._sha(payload['policy_revision'])
        for key in ('generation','population_worlds'):
            if type(payload[key]) is not int or payload[key]<0:raise ValueError('Invalid snapshot index counters')
        pages=payload['pages']
        if not isinstance(pages,list) or not pages or len(pages)>getattr(self,'_INDEX_PAGE_LIMIT',1024):
            raise ValueError('Snapshot index page limit exceeded')
        item_limit=getattr(self,'_PAGE_ITEM_LIMIT',2048)
        worlds,members=[],[]
        seen_kinds=[]
        tot_worlds=0;tot_members=0
        for ref in pages:
            if not isinstance(ref,dict) or set(ref.keys())!={'kind','count','artifact'}:raise ValueError('Invalid page reference')
            kind=ref['kind']
            if kind not in ('worlds','memberships'):raise ValueError('Invalid page reference kind')
            if kind=='worlds' and 'memberships' in seen_kinds:raise ValueError('Disordered page kinds')
            if seen_kinds and seen_kinds[-1]!=kind and kind in seen_kinds:raise ValueError('Disordered page kinds')
            seen_kinds.append(kind)
            count=ref['count']
            if type(count) is not int or not (1<=count<=item_limit):raise ValueError('Invalid page reference count')
            if kind=='worlds':
                tot_worlds+=count
                if tot_worlds>max_slots or tot_worlds>payload['population_worlds']:raise ValueError('Snapshot worlds capacity exceeded')
            else:
                tot_members+=count
                if tot_members>max_slots:raise ValueError('Snapshot memberships capacity exceeded')
            self.artifacts._validate_manifest(ref['artifact'])
            if ref['artifact']['uncompressed_length']>self._PAGE_BYTE_LIMIT:raise ValueError('Page byte cap exceeded')
            if protected is not None:protected.add(ref['artifact']['relative_key'])
            page=self.artifacts.get_json(ref['artifact'])
            if not isinstance(page,dict) or set(page.keys())!={'revision','kind','count','items'}:
                raise ValueError('Invalid snapshot page schema')
            if page['revision']!='catalog-snapshot-page-v2' or page['kind']!=kind:
                raise ValueError('Invalid snapshot page kind or revision')
            if type(page['count']) is not int or page['count']!=count or not isinstance(page['items'],list) or len(page['items'])!=count:
                raise ValueError('Invalid snapshot page count')
            if kind=='worlds':worlds.extend(page['items'])
            else:members.extend(page['items'])
        manifest=dict(
            revision='catalog-snapshot-v3' if v3 else 'catalog-snapshot-v2',
            **({k:payload[k] for k in ('policy_contract','registry','sampling_profile_revision','reserve_policy')} if v3 else {}),
            policy_revision=payload['policy_revision'],
            generation=payload['generation'],
            population_worlds=payload['population_worlds'],
            worlds=worlds,
            memberships=members,
        )
        if 'product_status' in payload:manifest['product_status']=payload['product_status']
        return self._manifest(manifest)

    def publish(self,ledger,*,fault=None,registry_v3=None,sampling_profile_revision=None,historically_complete=False):
        from .ingestion import atomic_json,verify_no_symlinks
        members=ledger.members();worlds=[]
        v3=getattr(ledger,'policy_contract',None) is not None
        if v3 and registry_v3 is None:raise ValueError('V3registry required')
        winning=sorted({row['world_id'] for row in members})
        if winning!=sorted(ledger.retained_worlds()):raise ValueError('Retained union differs')
        for wid in winning:
            receipt=ledger.receipt(wid)
            if receipt is None:raise ValueError('Missing winning receipt')
            entry={key:receipt[key] for key in ('world_id','identity','observation_id','artifact')}
            bundle=self._bundle(self.artifacts.get_json(entry['artifact']),entry)
            if v3:
                source=bundle['summaries'][0]
                if bundle['registry']!=registry_v3:raise ValueError('Mixed snapshot registries')
                entry.update({k:source[k] for k in ('registry_revision','sampling_profile_revision','source_extension_id')})
            entry['summary_artifacts']={str(side):self.artifacts.put_json(dict(
                revision='catalog-query-projection-v5' if v3 else 'catalog-query-projection-v3',
                **(dict(registry=registry_v3,sampling_profile_revision=entry['sampling_profile_revision'],source_extension_id=entry['source_extension_id']) if v3 else {}),
                world_id=wid,identity=entry['identity'],
                observation_id=entry['observation_id'],bundle_sha256=entry['artifact']['sha256'],
                summary_validator_sha256=self._query_validator_id(),
                row_count=sum(r['border_side']==side for r in bundle['summaries']),
                border_side=side,rows=self._pack_query_rows([r for r in bundle['summaries'] if r['border_side']==side],registry_v3) if v3 else [r for r in bundle['summaries'] if r['border_side']==side])) for side in (2048,4096,8192)}
            worlds.append(entry)
        extra={}
        if v3:
            from .reserve_policy import reserve_metadata
            extra=dict(policy_contract=ledger.policy_contract,registry=registry_v3,
                sampling_profile_revision=sampling_profile_revision,reserve_policy=reserve_metadata(historically_complete=historically_complete))
        manifest=self._manifest(dict(revision='catalog-snapshot-v3' if v3 else 'catalog-snapshot-v2',**extra,policy_revision=ledger.policy_revision,
            generation=ledger.generation(),population_worlds=ledger.population(),worlds=worlds,memberships=members))
        from .products import launch_definitions
        definitions=launch_definitions()
        product_ids={p['id'] for p in [definitions['realm'],*definitions.get('realm_sizes',[]),*definitions['presets'],*definitions['records']]}
        product_status={pid:dict(match=0,no_match=0,pending=0) for pid in sorted(product_ids)}
        for receipt in ledger.receipts():
            seen=set()
            for evaluation in receipt['evaluations']:
                pid=evaluation.get('product_id');status=evaluation.get('status')
                if (pid not in product_ids or pid in seen or status not in ('match','no_match','pending')
                        or evaluation.get('world_id')!=receipt['world_id']
                        or evaluation.get('observation_id')!=receipt['observation_id']):raise ValueError('Invalid product evaluation source')
                seen.add(pid)
                product_status[pid][status]+=1
            for pid in product_ids-seen:product_status[pid]['pending']+=1
        if product_status:manifest['product_status']=product_status
        self._manifest(manifest)
        sid=registry.digest(manifest)
        if self.current_path.exists():
            current=self.snapshot()
            if current['policy_revision']!=manifest['policy_revision']:raise ValueError('Policy namespace differs; rebuild separately')
            if current['generation']>manifest['generation']:raise ValueError('Stale publication generation')
            if current['generation']==manifest['generation'] and registry.digest(current)!=sid:
                # Derived read projections cannot rewrite an existing generation.
                def without_projections(value):
                    return dict({k:v for k,v in value.items() if k!='product_status'},worlds=[{k:v for k,v in e.items() if k!='summary_artifacts'} for e in value['worlds']])
                if without_projections(current)!=without_projections(manifest):raise ValueError('Same generation has conflicting content')
                manifest=current;sid=registry.digest(current)
        generation_path=verify_no_symlinks(self.generations_dir/(manifest['policy_revision']+'-'+str(manifest['generation'])+'.json'))
        existing_binding=None
        if generation_path.exists():
            prev=self._read(generation_path)
            if not isinstance(prev,dict) or prev.get('generation')!=manifest['generation'] or prev.get('snapshot_id')!=sid:
                raise ValueError('Conflicting immutable generation')
            existing_binding=prev
        snap_path=verify_no_symlinks(self.snapshots_dir/(sid+'.json'))
        if snap_path.exists():
            prev=self._read(snap_path)
            if not isinstance(prev,dict) or prev.get('snapshot_id')!=sid or prev.get('generation')!=manifest['generation']:
                raise ValueError('Immutable snapshot binding differs')
            if existing_binding is not None and prev!=existing_binding:
                raise ValueError('Immutable snapshot binding differs')
            existing_binding=prev
        if not generation_path.exists():
            for previous in self.snapshots_dir.glob('*.json'):
                existing=self._binding(previous.stem)
                if existing['generation']==manifest['generation']:
                    # Migrated workspaces retain snapshots from older policies.
                    # Generation counters are local to a policy's ledger.
                    historical=self.snapshot(existing['snapshot_id'])
                    if historical['policy_revision']!=manifest['policy_revision']:continue
                    if existing['snapshot_id']!=sid:raise ValueError('Conflicting historical generation')
                    if existing_binding is not None and existing!=existing_binding:
                        raise ValueError('Conflicting historical generation')
                    existing_binding=existing
                    break
        if existing_binding is not None:
            if (set(existing_binding)!={'revision','snapshot_id','generation','artifact'}
                    or existing_binding['revision']!='catalog-snapshot-binding-v2'
                    or type(existing_binding['generation']) is not int):raise ValueError('Invalid reused snapshot binding')
            reused=self._resolve_manifest(existing_binding['artifact'])
            if registry.digest(reused)!=sid:raise ValueError('Reused snapshot content differs')
            binding=existing_binding
        else:
            artifact=self._write_manifest(manifest)
            binding=dict(revision='catalog-snapshot-binding-v2',snapshot_id=sid,generation=manifest['generation'],artifact=artifact)
        if generation_path.exists():
            if self._read(generation_path)!=binding:raise ValueError('Conflicting immutable generation')
        else:
            atomic_json(generation_path,binding)
        if fault:fault('after_generation')
        if snap_path.exists():
            if self._read(snap_path)!=binding:raise ValueError('Immutable snapshot binding differs')
        else:atomic_json(snap_path,binding)
        if fault:fault('after_manifest')
        if not self.current_path.exists() or self._read(self.current_path)!=binding:atomic_json(self.current_path,binding)
        if fault:fault('after_pointer')
        return sid

    def _binding(self,snapshot_id=None):
        if snapshot_id is not None:self._sha(snapshot_id)
        binding=self._read(self.current_path if snapshot_id is None else self.snapshots_dir/(snapshot_id+'.json'))
        if not isinstance(binding,dict) or set(binding)!={'revision','snapshot_id','generation','artifact'} or binding['revision']!='catalog-snapshot-binding-v2':
            raise ValueError('Invalid snapshot binding')
        sid=self._sha(binding['snapshot_id'])
        if snapshot_id is None and self._read(self.snapshots_dir/(sid+'.json'))!=binding:
            raise ValueError('Current pointer lacks matching immutable binding')
        if snapshot_id is not None and sid!=snapshot_id:raise ValueError('Snapshot identity differs')
        if type(binding['generation']) is not int or binding['generation']<0:raise ValueError('Invalid binding generation')
        self.artifacts._validate_manifest(binding['artifact'])
        return binding

    def snapshot(self,snapshot_id=None):
        binding=self._binding(snapshot_id);manifest=self._resolve_manifest(binding['artifact'])
        if registry.digest(manifest)!=binding['snapshot_id'] or manifest['generation']!=binding['generation']:raise ValueError('Snapshot digest/generation mismatch')
        return manifest

    def snapshot_ids(self):
        from .ingestion import verify_no_symlinks
        verify_no_symlinks(self.snapshots_dir)
        if not self.snapshots_dir.exists():return []
        values=[]
        for path in sorted(self.snapshots_dir.iterdir()):
            verify_no_symlinks(path)
            if re.fullmatch(r'\.[a-f0-9]{64}\.json\.tmp\.[0-9]+\.[0-9]+',path.name) and path.is_file():continue
            if not path.is_file() or path.suffix!='.json':raise ValueError('Unexpected snapshot entry')
            values.append(self._sha(path.stem))
        return values

    def snapshots(self):
        values=[]
        for sid in self.snapshot_ids():
            manifest=self.snapshot(sid)
            values.append(dict(snapshot_id=sid,generation=manifest['generation'],worlds=len(manifest['worlds']),population_worlds=manifest['population_worlds']))
        return sorted(values,key=lambda row:(row['generation'],row['snapshot_id']))

    def iter_worlds(self,snapshot_id):
        """Verify one manifest, then stream each bound bundle without quadratic reloading."""
        manifest=self.snapshot(snapshot_id)
        for entry in manifest['worlds']:
            yield self._bundle(self.artifacts.get_json(entry['artifact']),entry)

    @staticmethod
    def _pack_query_rows(rows,definition):
        features=definition['features'];packed=[]
        for row in rows:
            blocks=[]
            for feature in features:
                block=row['features'][feature['id']]
                counts=block['counts']
                if feature['kind']=='biome_witness':counts=sum(int(bool(n))<<i for i,n in enumerate(counts))
                complete=sum(int(bool(n))<<i for i,n in enumerate(block['complete']))
                blocks.append([counts,complete,block['nearest_d2'],block['witness']])
            packed.append([row['layout_id'],row['anchor'],row['anchor_modes'],row['legacy'],blocks])
        return packed

    def _unpack_query_rows(self,rows,entry,definition,side,mode=None,*,validate=True,lazy_features=False):
        features=definition['features'];result=[];seen=set()
        slots={f['id']:(i,f) for i,f in enumerate(features)}
        count_bits=tuple(tuple(int(bool(n&(1<<i))) for i in range(4)) for n in range(16))
        complete_bits=tuple(tuple(bool(n&(1<<i)) for i in range(4)) for n in range(16))
        for packed in rows:
            if not isinstance(packed,list) or len(packed)!=5:raise ValueError('Invalid packed query row')
            lid,anchor,modes,legacy,blocks=packed;self._sha(lid)
            if (lid in seen or not isinstance(anchor,list) or len(anchor)!=2 or any(type(n)is not int or abs(n)>30000000 for n in anchor)
                    or not isinstance(modes,list) or not modes or len(modes)!=len(set(modes)) or any(m not in ('origin','recommended','world_spawn_estimated','world_spawn_observed') for m in modes)
                    or not isinstance(legacy,dict) or not isinstance(blocks,list) or len(blocks)!=len(features)):raise ValueError('Invalid packed query scope')
            seen.add(lid)
            if mode is not None and mode not in modes:continue
            if lazy_features and not validate:
                values=_PackedFeatures(blocks,slots)
            else:
                values={}
                for feature,block in zip(features,blocks):
                    if not isinstance(block,list) or len(block)!=4:raise ValueError('Invalid packed feature block')
                    counts,complete,distance,witness=block
                    if feature['kind']=='biome_witness':
                        if type(counts)is not int or not 0<=counts<=15:raise ValueError('Invalid packed biome mask')
                        counts=list(count_bits[counts])
                    elif not isinstance(counts,list) or len(counts)!=4 or (validate and any(type(n)is not int or not 0<=n<=200000 for n in counts)):raise ValueError('Invalid packed structure counts')
                    if type(complete)is not int or not 0<=complete<=15:raise ValueError('Invalid packed completeness mask')
                    complete=list(complete_bits[complete])
                    if validate and distance is not None and (type(distance)is not int or not 0<=distance<=2*(60000000**2)):raise ValueError('Invalid packed distance')
                    if validate and witness is not None and (not isinstance(witness,list) or len(witness)!=3 or any(type(witness[i])is not int or abs(witness[i])>30000000 for i in (0,2)) or (witness[1] is not None and (type(witness[1])is not int or not -64<=witness[1]<=319))):raise ValueError('Invalid packed XYZ witness')
                    if (witness is None)!=(distance is None):raise ValueError('Incomplete packed witness')
                    values[feature['id']]=dict(dimension=feature['dimension'],counts=counts,complete=complete,nearest_d2=distance,witness=witness)
            result.append(dict(revision='catalog-summary-v3',registry_revision=entry['registry_revision'],
                source_observation_id=entry['observation_id'],source_extension_id=entry['source_extension_id'],
                sampling_profile_revision=entry['sampling_profile_revision'],world_id=entry['world_id'],seed=entry['identity']['seed'],
                anchor=anchor,nether_anchor=[n//8 for n in anchor],anchor_modes=modes,border_side=side,layout_id=lid,features=values,legacy=legacy))
        return result

    def _projection(self,entry,side,mode=None,*,lazy_features=False):
        """The immutable snapshot binds this derived view to its verified raw bundle."""
        value=self.artifacts.get_json(entry['summary_artifacts'][str(side)])
        fields={'revision','world_id','identity','observation_id','bundle_sha256','border_side','rows'}
        if (not isinstance(value,dict) or
                (value.get('revision'),frozenset(value)) not in (
                    ('catalog-query-projection-v2',frozenset(fields)),
                    ('catalog-query-projection-v3',frozenset(fields|{'summary_validator_sha256','row_count'})),
                    ('catalog-query-projection-v4',frozenset(fields|{'summary_validator_sha256','row_count','registry','sampling_profile_revision','source_extension_id'})),
                    ('catalog-query-projection-v5',frozenset(fields|{'summary_validator_sha256','row_count','registry','sampling_profile_revision','source_extension_id'})))
                or any(value[k]!=entry[k] for k in ('world_id','identity','observation_id'))
                or value['bundle_sha256']!=entry['artifact']['sha256'] or value['border_side']!=side
                or not isinstance(value['rows'],list) or len(value['rows'])>1024):raise ValueError('Invalid query projection binding')
        v3=value['revision'] in ('catalog-query-projection-v4','catalog-query-projection-v5')
        current=value['revision'] in ('catalog-query-projection-v3','catalog-query-projection-v4','catalog-query-projection-v5')
        if v3 and (registry.digest(value['registry'])!=entry['registry_revision'] or any(value[k]!=entry[k] for k in ('sampling_profile_revision','source_extension_id'))):raise ValueError('Projected v3evidence differs')
        if current:
            self._sha(value['summary_validator_sha256'])
            if type(value['row_count']) is not int or value['row_count']!=len(value['rows']):raise ValueError('Projection row count mismatch')
        trusted=current and value['summary_validator_sha256']==self._query_validator_id()
        if value['revision']=='catalog-query-projection-v5':
            value=dict(value,rows=self._unpack_query_rows(value['rows'],entry,value['registry'],side,mode,validate=not trusted,lazy_features=lazy_features))
        seen=set()
        for row in value['rows']:
            if (not isinstance(row,dict) or row.get('world_id')!=entry['world_id'] or row.get('source_observation_id')!=entry['observation_id']
                    or row.get('seed')!=entry['identity']['seed'] or row.get('border_side')!=side
                    or row.get('layout_id') in seen):raise ValueError('Invalid projected summary source')
            seen.add(row['layout_id'])
            if not trusted:
                if v3:
                    from .codec import validate_summary_v3
                    validate_summary_v3(row,registry=value['registry'])
                else:
                    from .codec import validate_summary_v2
                    validate_summary_v2(row)
        return value['rows']

    def iter_query_summaries(self,manifest,side,mode,*,lazy_features=False):
        """Read only the requested border; old immutable snapshots use their bundles."""
        for entry in manifest['worlds']:
            rows=self._projection(entry,side,mode,lazy_features=lazy_features) if 'summary_artifacts' in entry else self._bundle(self.artifacts.get_json(entry['artifact']),entry)['summaries']
            for row in rows:
                if row['border_side']==side and mode in row['anchor_modes']:
                    # Current projections are exact views of fully validated writer
                    # input, bound by validator revision and the immutable CAS root.
                    yield row

    def world(self,snapshot_id,world_id):
        self._sha(world_id);manifest=self.snapshot(snapshot_id)
        entry=next((entry for entry in manifest['worlds'] if entry['world_id']==world_id),None)
        if entry is None:raise KeyError('World is not in snapshot')
        return self._bundle(self.artifacts.get_json(entry['artifact']),entry)

    def pin(self,snapshot_id,world_id):
        """Explicit pin under writer ownership; historical snapshots already protect shares."""
        from .ingestion import atomic_json
        self.world(snapshot_id,world_id)
        path=self.base/'pins.json';pins=self._read(path,max_bytes=256<<10) if path.exists() else []
        if not isinstance(pins,list) or len(pins)>1000:raise ValueError('Invalid pins')
        value=dict(snapshot_id=snapshot_id,world_id=world_id)
        if value not in pins:
            if len(pins)>=1000:raise ValueError('Explicit pin capacity1000 reached')
            pins.append(value)
        atomic_json(path,pins)

    def cleanup(self,ledger,*,mode='dry_run',check=lambda:None):
        """Fail closed before any move; immutable history and resumable receipts are roots."""
        from .ingestion import verify_no_symlinks,strict_json_loads
        from .artifacts import _CONTENT_ADDR_RE,_fsync_dir
        if mode not in ('dry_run','quarantine','delete','reclaim'):raise ValueError('Unknown cleanup mode')
        if mode=='reclaim' and not ledger.queue._depth:raise ValueError('Reclamation requires writer ownership')
        check();protected=set();known={};verified_bundles=set()
        def referenced_manifests():
            for row in self.snapshots():
                check()
                binding=self._binding(row['snapshot_id']);manifest=self._resolve_manifest(binding['artifact'],protected=protected)
                if registry.digest(manifest)!=binding['snapshot_id'] or manifest['generation']!=binding['generation']:raise ValueError('Snapshot digest/generation mismatch')
                known[binding['snapshot_id']]=(manifest['policy_revision'],binding)
                yield manifest
            verify_no_symlinks(self.generations_dir)
            if not self.generations_dir.exists():return
            for path in self.generations_dir.iterdir():
                check()
                verify_no_symlinks(path)
                if re.fullmatch(r'\.[a-f0-9]{64}-[0-9]+\.json\.tmp\.[0-9]+\.[0-9]+',path.name) and path.is_file():continue
                match=re.fullmatch(r'([a-f0-9]{64})-([0-9]+)\.json',path.name)
                if not match or not path.is_file():raise ValueError('Invalid generation entry')
                binding=self._read(path)
                if not isinstance(binding,dict) or set(binding)!={'revision','snapshot_id','generation','artifact'} or binding['revision']!='catalog-snapshot-binding-v2':raise ValueError('Invalid generation binding')
                sid=self._sha(binding['snapshot_id'])
                if sid in known:
                    policy,expected=known[sid]
                    if policy!=match[1] or str(binding['generation'])!=match[2] or binding!=expected:raise ValueError('Generation binding mismatch')
                    continue
                manifest=self._resolve_manifest(binding['artifact'],protected=protected)
                if registry.digest(manifest)!=sid or manifest['policy_revision']!=match[1] or str(manifest['generation'])!=match[2] or binding['generation']!=manifest['generation']:
                    raise ValueError('Generation binding mismatch')
                known[sid]=(manifest['policy_revision'],binding)
                yield manifest
        for manifest in referenced_manifests():
            check()
            for entry in manifest['worlds']:
                check()
                key=entry['artifact']['relative_key']
                proof=(key,entry['world_id'],entry['observation_id'],registry.digest(entry['identity']))
                if proof not in verified_bundles:
                    bundle=self._bundle(self.artifacts.get_json(entry['artifact']),entry)
                    if bundle.get('extension_artifact') is not None:protected.add(bundle['extension_artifact']['relative_key'])
                    protected.add(key);verified_bundles.add(proof)
                for side,artifact in entry.get('summary_artifacts',{}).items():
                    check()
                    if artifact['relative_key'] not in protected:
                        for row in self._projection(entry,int(side)):
                            if row['revision']=='catalog-summary-v3':
                                from .codec import validate_summary_v3
                                validate_summary_v3(row,registry=manifest['registry'])
                            else:
                                from .codec import validate_summary_v2
                                validate_summary_v2(row)
                        protected.add(artifact['relative_key'])
        if self.current_path.exists():self.snapshot()
        pins_path=verify_no_symlinks(self.base/'pins.json')
        if pins_path.exists():
            pins=self._read(pins_path,max_bytes=256<<10)
            if not isinstance(pins,list) or len(pins)>1000:raise ValueError('Invalid pins')
            for pin in pins:
                check()
                if not isinstance(pin,dict) or set(pin)!={'snapshot_id','world_id'}:raise ValueError('Invalid pin')
                self.world(pin['snapshot_id'],pin['world_id'])
        wanted=set(ledger.retained_worlds())
        active=ledger.conn.execute("SELECT value FROM automation_meta WHERE key='verification_worlds'").fetchone()
        if active:
            ids=strict_json_loads(active[0])
            if not isinstance(ids,list) or len(ids)>231928 or any(not isinstance(w,str) or not _HEX64_RE.fullmatch(w) for w in ids):raise ValueError('Invalid verification roots')
            wanted.update(ids)
        if not callable(getattr(ledger,'receipts',None)):raise ValueError('All receipts are required for safe cleanup')
        receipts=ledger.receipts()
        for receipt in receipts:
            check()
            if not isinstance(receipt,dict) or not isinstance(receipt.get('replay'),dict):raise ValueError('Malformed replay receipt')
            if receipt['world_id'] in wanted or receipt['replay'].get('resumable') or receipt['replay'].get('verification_in_progress'):
                proof=(receipt['artifact']['relative_key'],receipt['world_id'],receipt['observation_id'],registry.digest(receipt['identity']))
                if proof not in verified_bundles:
                    bundle=self._bundle(self.artifacts.get_json(receipt['artifact']),receipt)
                    if bundle.get('extension_artifact') is not None:protected.add(bundle['extension_artifact']['relative_key'])
                    verified_bundles.add(proof)
                protected.add(receipt['artifact']['relative_key']);wanted.discard(receipt['world_id'])
        if wanted:raise ValueError('Incomplete receipt roots')
        inventories={}
        for directory in (self.objects_dir,self.quarantine_dir):
            verify_no_symlinks(directory);entries=[]
            if directory.exists():
                for path in directory.rglob('*'):
                    check()
                    verify_no_symlinks(path)
                    if path.is_dir():continue
                    relative=path.relative_to(directory).as_posix()
                    if relative.startswith('.tmp/') and directory==self.objects_dir:continue
                    if not path.is_file() or not _CONTENT_ADDR_RE.fullmatch(relative):raise ValueError('Unexpected object namespace entry')
                    if relative not in protected:entries.append((relative,path,path.stat().st_size))
            inventories[directory]=sorted(entries)
        selected=inventories[self.quarantine_dir if mode=='delete' else self.objects_dir]
        # Validate every destination before the first mutation.
        if mode in ('quarantine','reclaim'):
            for key,source,_ in selected:
                check()
                target=verify_no_symlinks(self.quarantine_dir/key)
                if target.exists():raise ValueError('Quarantine destination exists; inspect duplicate first')
        for key,path,_ in selected:
            check()
            if mode=='delete':path.unlink();_fsync_dir(path.parent)
            elif mode in ('quarantine','reclaim'):
                target=self.quarantine_dir/key;target.parent.mkdir(parents=True,exist_ok=True)
                path.replace(target);_fsync_dir(path.parent);_fsync_dir(target.parent)
        if mode=='reclaim':
            # The caller holds writer ownership; the verified roots cannot change
            # between quarantine and deletion. A crash leaves recoverable orphans.
            for key,_,_ in [*inventories[self.quarantine_dir],*selected]:
                check();path=verify_no_symlinks(self.quarantine_dir/key)
                path.unlink();_fsync_dir(path.parent)
        reported=[*inventories[self.quarantine_dir],*selected] if mode=='reclaim' else selected
        return dict(mode=mode,candidates=[key for key,_,_ in reported],bytes=sum(n for _,_,n in reported))

    def cleanup_completed_staging(self,ledger,*,mode='dry_run',check=lambda:None):
        """Caller holds supervisor/writer ownership and verifies CAS roots first.

        Only acknowledged, explicitly non-resumable jobs are disposable. Unknown
        and failed work is preserved; quarantine is separately revalidated.
        """
        import shutil
        import json
        from .ingestion import verify_no_symlinks
        from .artifacts import _fsync_dir
        if mode not in ('dry_run','quarantine','delete'):raise ValueError('Unknown cleanup mode')
        if not ledger.queue._depth:raise ValueError('Staging reclamation requires writer ownership')
        staging=verify_no_symlinks(self.root/'staging')
        quarantine=verify_no_symlinks(self.base/'staging-quarantine')
        jobs={}
        for row in ledger.queue.conn.execute("SELECT id,identity,checkpoint,snapshot_id FROM jobs WHERE state='complete'"):
            check();task=self._sha(row['id']);receipt=ledger.receipt(models.world_id(json.loads(row['identity'])))
            if receipt is None or receipt['replay'].get('resumable') is not False:continue
            sid=self._sha(row['snapshot_id'])
            if not verify_no_symlinks(self.snapshots_dir/(sid+'.json')).is_file():continue
            self.snapshot(sid)
            checkpoint=verify_no_symlinks(row['checkpoint'])
            parts=checkpoint.relative_to(staging/task).parts
            if len(parts)!=2 or not parts[0].isdigit() or parts[1]!='observation.json':raise ValueError('Unexpected completed checkpoint')
            jobs[task]=row
        if quarantine.exists():
            for path in quarantine.iterdir():
                check();verify_no_symlinks(path);self._sha(path.name)
                if not path.is_dir() or path.name not in jobs:raise ValueError('Unbound staging quarantine')
        candidates=[]
        base=quarantine if mode=='delete' else staging
        for task in sorted(jobs):
            check();source=verify_no_symlinks(base/task)
            if not source.exists():continue
            if not source.is_dir():raise ValueError('Completed staging must be a directory')
            for n,path in enumerate(source.rglob('*')):
                check();verify_no_symlinks(path)
                if n>=10000:raise ValueError('Completed staging entry cap')
            target=verify_no_symlinks(quarantine/task)
            if mode=='quarantine' and target.exists():raise ValueError('Staging quarantine collision')
            candidates.append((task,source,target))
            if len(candidates)>=100:break
        # Validate every candidate before the first move; never inspect a DB PID.
        for task,source,target in candidates:
            check()
            if mode=='quarantine':
                quarantine.mkdir(parents=True,exist_ok=True);source.replace(target);_fsync_dir(staging);_fsync_dir(quarantine)
            elif mode=='delete':shutil.rmtree(source);_fsync_dir(quarantine)
        return dict(mode=mode,candidates=[task for task,_,_ in candidates])
