"""Durable segmented catalog with content-addressed tree manifests and SQLite metadata."""
from datetime import datetime, timezone
from pathlib import Path
import base64
import hashlib
import json
import re
import sqlite3
import threading

from .artifacts import ArtifactStore
from . import codec
from . import geometry
from . import models
from . import registry

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_PERSONAL_FILES = (
    "seeds.db",
    "personal.db",
    "seed_search.db",
    "runs.db",
    "world_search.db",
    "evaluations.db",
    "catalog.sqlite",
)
_FORBIDDEN_PERSONAL_TABLES = {
    "personal_policy",
    "evaluations",
    "seed_candidates",
    "runs",
    "search_runs",
}
SCHEMA_REVISION = "catalog-segmented-pilot-v1"


def _layout_sort_key(s: dict) -> tuple:
    anchor = s["anchor"]
    return (s["world_id"], s["border_side"], anchor[0], anchor[1], s["layout_id"])


class SegmentedCatalog:
    """Segmented catalog store with content-addressed tree manifests and atomic promotion."""

    def __init__(self, root: str | Path, *, leaf_entries: int = 256, fanout: int = 128):
        if not root:
            raise ValueError("Root directory must be provided")

        if type(leaf_entries) is not int or leaf_entries < 1 or leaf_entries > 256:
            raise ValueError("leaf_entries must be an integer between 1 and 256")
        if type(fanout) is not int or fanout < 2 or fanout > 128:
            raise ValueError("fanout must be an integer between 2 and 128")

        self.leaf_entries = leaf_entries
        self.fanout = fanout

        raw_path = Path(root)
        if raw_path.is_symlink():
            raise ValueError(f"Root path cannot be a symlink: {root}")

        # Check symlink components along the path
        curr = Path(raw_path.parts[0]) if raw_path.is_absolute() else Path(".")
        for part in raw_path.parts[(1 if raw_path.is_absolute() else 0):]:
            curr = curr / part
            if curr.is_symlink():
                raise ValueError(f"Symlink component detected in root path: {curr}")

        self.root = raw_path.resolve()
        if raw_path.is_symlink() or self.root.is_symlink():
            raise ValueError(f"Root path cannot be a symlink: {root}")

        # Enforce dedicated root; reject forbidden personal DB files and existing catalog.sqlite
        for forbidden in _FORBIDDEN_PERSONAL_FILES:
            if (self.root / forbidden).exists() or (raw_path / forbidden).exists():
                raise ValueError(f"Forbidden database file {forbidden} detected in root; reuse prohibited")

        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink() or raw_path.is_symlink():
            raise ValueError(f"Root path cannot be a symlink: {root}")

        self.db_path = self.root / "pilot.sqlite"
        for name in ("pilot.sqlite", "pilot.sqlite-wal", "pilot.sqlite-shm"):
            if (self.root / name).is_symlink():
                raise ValueError("Symlink database files are not allowed")

        if self.db_path.exists():
            try:
                with sqlite3.connect(self.db_path.as_uri() + "?mode=ro", uri=True) as probe:
                    tables = {row[0] for row in probe.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if tables & _FORBIDDEN_PERSONAL_TABLES:
                        raise ValueError("Personal database schema detected; reuse prohibited")
                    if "schema_meta" not in tables:
                        raise ValueError("Incompatible database: missing schema_meta marker")
                    rows = probe.execute("SELECT revision, status FROM schema_meta").fetchall()
                    if rows != [(SCHEMA_REVISION, "active")]:
                        raise ValueError("Incompatible catalog schema marker")
            except sqlite3.Error as error:
                raise ValueError("Not an existing pilot catalog database") from error

        self.artifacts = ArtifactStore(self.root / "artifacts")
        self._lock = threading.RLock()
        self.conn = None
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0,
            isolation_level=None,
        )
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = FULL;")

        cursor = conn.cursor()
        existing_tables = {
            r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        }

        if existing_tables & _FORBIDDEN_PERSONAL_TABLES:
            conn.close()
            raise ValueError("Personal database schema detected in pilot database; reuse prohibited")

        if existing_tables:
            if "schema_meta" not in existing_tables:
                conn.close()
                raise ValueError("Incompatible database: missing schema_meta marker")
            rows = cursor.execute("SELECT revision, status FROM schema_meta;").fetchall()
            if not rows or rows[0][0] != SCHEMA_REVISION:
                conn.close()
                raise ValueError(f"Incompatible database schema revision: {rows}")
        else:
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
                    CREATE TABLE artifact_ref (
                        sha256 TEXT PRIMARY KEY CHECK (length(sha256)=64),
                        relative_key TEXT NOT NULL UNIQUE,
                        byte_length INTEGER NOT NULL CHECK (byte_length>=0),
                        uncompressed_length INTEGER NOT NULL CHECK (uncompressed_length>=0),
                        codec TEXT NOT NULL,
                        published_at TEXT NOT NULL
                    );
                """)

                cursor.execute("""
                    CREATE TABLE snapshot_root (
                        snapshot_id TEXT PRIMARY KEY CHECK (length(snapshot_id)=64),
                        parent_id TEXT REFERENCES snapshot_root(snapshot_id),
                        manifest_sha256 TEXT NOT NULL REFERENCES artifact_ref(sha256),
                        tree_root_sha256 TEXT NOT NULL REFERENCES artifact_ref(sha256),
                        header_json TEXT NOT NULL,
                        world_count INTEGER NOT NULL CHECK (world_count>=0),
                        layout_count INTEGER NOT NULL CHECK (layout_count>=0),
                        published_at TEXT NOT NULL
                    );
                """)

                cursor.execute("""
                    CREATE TABLE observation_ref (
                        snapshot_id TEXT NOT NULL REFERENCES snapshot_root(snapshot_id) ON DELETE CASCADE,
                        world_id TEXT NOT NULL CHECK (length(world_id)=64),
                        observation_id TEXT NOT NULL CHECK (length(observation_id)=64),
                        seed TEXT NOT NULL,
                        manifest_sha256 TEXT NOT NULL REFERENCES artifact_ref(sha256),
                        PRIMARY KEY (snapshot_id, world_id)
                    );
                """)

                cursor.execute("""
                    CREATE TABLE leaf_segment (
                        segment_id TEXT PRIMARY KEY CHECK (length(segment_id)=64),
                        manifest_sha256 TEXT NOT NULL REFERENCES artifact_ref(sha256),
                        world_id TEXT NOT NULL CHECK (length(world_id)=64),
                        layout_count INTEGER NOT NULL CHECK (layout_count>=0),
                        created_at TEXT NOT NULL
                    );
                """)

                cursor.execute("""
                    CREATE TABLE snapshot_membership (
                        snapshot_id TEXT NOT NULL REFERENCES snapshot_root(snapshot_id) ON DELETE CASCADE,
                        segment_id TEXT NOT NULL REFERENCES leaf_segment(segment_id),
                        ordinal INTEGER NOT NULL,
                        PRIMARY KEY (snapshot_id, ordinal),
                        UNIQUE (snapshot_id, segment_id)
                    );
                """)

                cursor.execute("CREATE INDEX idx_obs_snap ON observation_ref(snapshot_id);")
                cursor.execute("CREATE INDEX idx_obs_world ON observation_ref(world_id);")
                cursor.execute("CREATE INDEX idx_leaf_world ON leaf_segment(world_id);")
                cursor.execute("CREATE INDEX idx_mem_snap ON snapshot_membership(snapshot_id, ordinal);")
                cursor.execute("COMMIT;")
            except Exception:
                cursor.execute("ROLLBACK;")
                conn.close()
                raise

        self.conn = conn

    def _check_open(self) -> None:
        if self.conn is None:
            raise RuntimeError("SegmentedCatalog is closed")

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            if self.conn is not None:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None

    def __enter__(self) -> "SegmentedCatalog":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _build_tree(self, leaf_descriptors: list[dict], new_artifacts: dict[str, dict]) -> dict:
        """Build a balanced content-addressed manifest tree with bounded fanout."""
        current_items = leaf_descriptors
        level = 1

        while True:
            if len(current_items) <= self.fanout:
                node_payload = {
                    "kind": "tree_node",
                    "level": level,
                    "fanout": self.fanout,
                    "child_count": len(current_items),
                    "layout_count": sum(c["layout_count"] for c in current_items),
                    "children": current_items,
                }
                node_bytes = json.dumps(
                    node_payload, sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode("utf-8")
                if len(node_bytes) > 1024 * 1024:
                    raise ValueError("Tree node uncompressed size exceeds 1MiB")
                m = self.artifacts.put_json(node_payload)
                new_artifacts[m["sha256"]] = m
                return m

            next_items = []
            for i in range(0, len(current_items), self.fanout):
                chunk = current_items[i : i + self.fanout]
                node_payload = {
                    "kind": "tree_node",
                    "level": level,
                    "fanout": self.fanout,
                    "child_count": len(chunk),
                    "layout_count": sum(c["layout_count"] for c in chunk),
                    "children": chunk,
                }
                node_bytes = json.dumps(
                    node_payload, sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode("utf-8")
                if len(node_bytes) > 1024 * 1024:
                    raise ValueError("Tree node uncompressed size exceeds 1MiB")
                m = self.artifacts.put_json(node_payload)
                new_artifacts[m["sha256"]] = m
                next_items.append({
                    "kind": "tree_node",
                    "sha256": m["sha256"],
                    "relative_key": m["relative_key"],
                    "byte_length": m["byte_length"],
                    "uncompressed_length": m["uncompressed_length"],
                    "codec": m["codec"],
                    "layout_count": node_payload["layout_count"],
                })
            current_items = next_items
            level += 1

    def _collect_leaf_manifests_from_tree(self, node_manifest, _depth=0, _visited=None):
        """Validate bounded tree nodes and their counts; never trust SQL membership alone."""
        if _depth>32:raise ValueError('Manifest tree depth exceeds32')
        visited=set() if _visited is None else _visited
        if node_manifest['sha256'] in visited:raise ValueError('Repeated/cyclic tree node')
        visited.add(node_manifest['sha256'])
        node=self.artifacts.get_json(node_manifest)
        if len(registry.canonical_json(node))>1<<20:raise ValueError('Manifest node exceeds1MiB')
        if node.get('kind')=='leaf':return [node_manifest]
        if node.get('kind')!='tree_node':raise ValueError('Invalid tree kind')
        children=node.get('children');fanout=node.get('fanout')
        if type(fanout) is not int or not 2<=fanout<=128 or not isinstance(children,list) or not 1<=len(children)<=fanout:
            raise ValueError('Invalid tree fanout/children')
        if node.get('child_count')!=len(children) or node.get('layout_count')!=sum(c['layout_count'] for c in children):
            raise ValueError('Invalid tree child/layout counts')
        leaves=[]
        for child in children:
            manifest={k:child[k] for k in ('sha256','relative_key','byte_length','uncompressed_length','codec')}
            if child.get('kind')=='leaf':
                if child['sha256'] in visited:raise ValueError('Duplicate tree leaf')
                visited.add(child['sha256']);leaves.append(manifest)
            elif child.get('kind')=='tree_node':leaves.extend(self._collect_leaf_manifests_from_tree(manifest,_depth+1,visited))
            else:raise ValueError('Invalid child kind')
        return leaves

    def _verified_membership(self,sid):
        """Bind SQL header/membership to content-addressed root without raw samples."""
        with self._lock:
            row=self.conn.execute('SELECT manifest_sha256,tree_root_sha256,header_json,world_count,layout_count FROM snapshot_root WHERE snapshot_id=?',(sid,)).fetchone()
            if row is None:raise ValueError('Unknown snapshot')
            def manifest(sha):
                record=self.conn.execute('SELECT sha256,relative_key,byte_length,uncompressed_length,codec FROM artifact_ref WHERE sha256=?',(sha,)).fetchone()
                if record is None:raise ValueError('Missing manifest record')
                return dict(zip(('sha256','relative_key','byte_length','uncompressed_length','codec'),record))
            root=self.artifacts.get_json(manifest(row[0]))
            descriptor={k:v for k,v in root.items() if k!='snapshot_id'}
            if root.get('snapshot_id')!=sid or registry.digest(descriptor)!=sid:raise ValueError('Root descriptor identity mismatch')
            if (root.get('schema_revision')!=SCHEMA_REVISION or root.get('registry_revision')!=registry.REGISTRY_REVISION
                or root.get('geometry_revision')!=models.GEOMETRY_REVISION or root.get('summary_revision')!=models.SUMMARY_REVISION
                or root.get('policy_sha256')!=registry.digest(registry.POLICY) or root.get('score_revision')!=registry.POLICY['score']['revision']):
                raise ValueError('Root revision mismatch')
            if root.get('header')!=json.loads(row[2]) or root.get('world_count')!=row[3] or root.get('layout_count')!=row[4] or root.get('tree_root_sha256')!=row[1]:
                raise ValueError('Root metadata mismatch')
            reachable=self._collect_leaf_manifests_from_tree(manifest(row[1]))
            membership=self.conn.execute("""SELECT sm.segment_id,ar.sha256,ar.relative_key,ar.byte_length,ar.uncompressed_length,ar.codec
                FROM snapshot_membership sm JOIN leaf_segment ls ON sm.segment_id=ls.segment_id
                JOIN artifact_ref ar ON ls.manifest_sha256=ar.sha256 WHERE sm.snapshot_id=? ORDER BY sm.ordinal""",(sid,)).fetchall()
            if len(reachable)!=len(membership):raise ValueError('Root membership count mismatch')
            for expected,actual in zip(reachable,membership):
                if expected!=dict(zip(('sha256','relative_key','byte_length','uncompressed_length','codec'),actual[1:])):
                    raise ValueError('Root membership identity/order mismatch')
            return membership

    def publish(
        self,
        observations: list[dict],
        layouts: list[dict],
        *,
        parent: str | None = None,
        replace_worlds: tuple[str, ...] | list[str] | set[str] = (),
        prepare_publication=None,
    ) -> str:
        """Publish an immutable generation after optional dependent-file readiness.

        prepare_publication(store, snapshot_id) runs with the new metadata visible
        only on this connection, before COMMIT. It must durably prepare/check its
        dependencies and raise on failure. Other connections keep the old latest
        snapshot. Failed callbacks can leave unreachable immutable files; retry
        must be idempotent. Callbacks must not commit or mutate this connection.
        """
        self._check_open()

        if prepare_publication is not None and not callable(prepare_publication):
            raise ValueError('prepare_publication must be callable')

        if not isinstance(observations, list) or not isinstance(layouts, list):
            raise ValueError("Observations and layouts must be lists")
        if not observations:
            raise ValueError("Cannot publish snapshot with zero observations")
        if not layouts:
            raise ValueError("Cannot publish snapshot with zero layouts")

        replace_set = set(replace_worlds)
        for wid in replace_set:
            if not isinstance(wid, str) or not _HEX64_RE.fullmatch(wid):
                raise ValueError(f"Invalid world_id in replace_worlds: {wid}")

        if parent is None and replace_set:
            raise ValueError("replace_worlds cannot be specified without a parent snapshot")

        # Validate parent if specified
        parent_header = None
        parent_world_ids = set()
        parent_obs_refs = {}
        parent_leaf_items = {}  # world_id -> list of leaf item dicts

        with self._lock:
            cur = self.conn.cursor()
            if parent is not None:
                if not isinstance(parent, str) or not _HEX64_RE.fullmatch(parent):
                    raise ValueError(f"Invalid parent snapshot_id: {parent}")
                cur.execute(
                    "SELECT snapshot_id, header_json FROM snapshot_root WHERE snapshot_id = ?;",
                    (parent,),
                )
                p_row = cur.fetchone()
                if not p_row:
                    raise ValueError(f"Unknown parent snapshot: {parent}")
                parent_header = json.loads(p_row[1])

                cur.execute(
                    "SELECT world_id, observation_id, seed, manifest_sha256 FROM observation_ref WHERE snapshot_id = ?;",
                    (parent,),
                )
                for w_row in cur.fetchall():
                    wid, oid, seed_str, m_sha = w_row
                    parent_world_ids.add(wid)
                    parent_obs_refs[wid] = {
                        "world_id": wid,
                        "observation_id": oid,
                        "seed": seed_str,
                        "manifest_sha256": m_sha,
                    }

                cur.execute(
                    """
                    SELECT ls.segment_id, ls.manifest_sha256, ls.world_id, ls.layout_count,
                           ar.relative_key, ar.byte_length, ar.uncompressed_length, ar.codec
                    FROM snapshot_membership sm
                    JOIN leaf_segment ls ON sm.segment_id = ls.segment_id
                    JOIN artifact_ref ar ON ls.manifest_sha256 = ar.sha256
                    WHERE sm.snapshot_id = ?
                    ORDER BY sm.ordinal ASC;
                    """,
                    (parent,),
                )
                for l_row in cur.fetchall():
                    seg_id, m_sha, wid, l_cnt, rk, bl, ul, codec_name = l_row
                    item = {
                        "kind": "leaf",
                        "sha256": m_sha,
                        "relative_key": rk,
                        "byte_length": bl,
                        "uncompressed_length": ul,
                        "codec": codec_name,
                        "segment_id": seg_id,
                        "world_id": wid,
                        "layout_count": l_cnt,
                    }
                    if wid not in parent_leaf_items:
                        parent_leaf_items[wid] = []
                    parent_leaf_items[wid].append(item)

        # Validate existing immutable membership before deriving an appended root.
        if parent is not None:self._verified_membership(parent)

        for wid in replace_set:
            if wid not in parent_world_ids:
                raise ValueError(f"replace_worlds specifies world {wid} not present in parent snapshot")

        # Validate input observations
        batch_obs_by_id = {}
        batch_obs_by_world = {}
        batch_header = None

        for obs in observations:
            models.validate_observation(obs)
            oid = models.observation_id(obs)
            if oid in batch_obs_by_id:
                raise ValueError(f"Duplicate observation in publication batch: {oid}")
            wid = models.world_id(obs["identity"])
            if wid in batch_obs_by_world:
                raise ValueError(f"Only one observation per world is allowed in a publication batch: {wid}")

            obs_header = {k: v for k, v in sorted(obs["identity"].items()) if k != "seed"}
            if batch_header is None:
                batch_header = obs_header
            elif obs_header != batch_header:
                raise ValueError("Mixed build/settings identities in publication batch")

            batch_obs_by_id[oid] = obs
            batch_obs_by_world[wid] = obs

        if parent is not None:
            if batch_header != parent_header:
                raise ValueError("Incompatible header with parent snapshot")
            for wid in batch_obs_by_world:
                if wid in parent_world_ids and wid not in replace_set and models.observation_id(batch_obs_by_world[wid])!=parent_obs_refs[wid]['observation_id']:
                    raise ValueError(
                        f"Conflict: world {wid} already exists in parent snapshot; replacement requires explicit replace_worlds"
                    )

        for wid in replace_set:
            if wid not in batch_obs_by_world:
                raise ValueError(f"replace_worlds specifies world {wid} without providing replacement observation")

        current_header = batch_header if parent is None else parent_header

        # Validate input layouts
        batch_layouts_by_world = {wid: [] for wid in batch_obs_by_world}
        seen_lids = set()

        for summary in layouts:
            codec.validate_summary(summary)
            lid = summary["layout_id"]
            if lid in seen_lids:
                raise ValueError(f"Duplicate layout in publication batch: {lid}")
            seen_lids.add(lid)

            oid = summary["observation_id"]
            if oid not in batch_obs_by_id:
                raise ValueError(f"Layout {lid} references observation_id {oid} not in supplied observations")

            obs = batch_obs_by_id[oid]
            wid = summary["world_id"]
            if wid != models.world_id(obs["identity"]):
                raise ValueError(f"Layout {lid} world_id does not match observation world_id")
            if summary["seed"] != obs["identity"]["seed"]:
                raise ValueError(f"Layout {lid} seed does not match observation seed")
            if tuple(summary["anchor"]) not in geometry.anchors():
                raise ValueError(f"Layout {lid} has unsupported anchor {summary['anchor']}")
            if summary["border_side"] not in registry.SIDES:
                raise ValueError(f"Layout {lid} has unsupported border_side {summary['border_side']}")

            packed = codec.pack_summary(summary)
            if len(packed) != 364:
                raise ValueError(f"Packed summary payload must be 364 bytes, got {len(packed)}")
            bhash = hashlib.sha256(packed).hexdigest()
            b64 = base64.b64encode(packed).decode("ascii")

            batch_layouts_by_world[wid].append((summary, packed, bhash, b64))

        for wid, l_list in batch_layouts_by_world.items():
            if not l_list:
                raise ValueError(f"World {wid} has zero layouts in publication batch")

        # Identical replay against the latest parent is a no-op. A caller must
        # explicitly replace a world to change either observation or layout set.
        duplicates=set(batch_obs_by_world)&parent_world_ids-replace_set
        if duplicates:
            expected={wid:{} for wid in duplicates}
            for segment in self.iter_segments(parent):
                for row in segment['layouts']:
                    if row['world_id'] in expected:expected[row['world_id']][row['layout_id']]=codec.pack_summary(row)
            for wid in duplicates:
                actual={s['layout_id']:packed for s,packed,_,_ in batch_layouts_by_world[wid]}
                if expected[wid]!=actual:raise ValueError('Conflict: existing world layout change requires explicit replace_worlds')
                obs=batch_obs_by_world.pop(wid);batch_obs_by_id.pop(models.observation_id(obs));batch_layouts_by_world.pop(wid)
            if not batch_obs_by_world:return parent

        # DURABILITY FIRST: Stage and write new artifacts
        new_artifacts = {}
        batch_obs_manifests = {}
        for oid, obs in batch_obs_by_id.items():
            m = self.artifacts.put_json(obs)
            batch_obs_manifests[oid] = m
            new_artifacts[m["sha256"]] = m

        # Determine snapshot worlds: retained from parent + new/replaced from batch
        all_worlds = set()
        if parent is not None:
            retained_worlds = [w for w in parent_world_ids if w not in replace_set]
            all_worlds.update(retained_worlds)
        all_worlds.update(batch_obs_by_world.keys())

        # Build leaves for new/replaced worlds
        new_leaf_items = {}  # wid -> list of leaf item dicts
        new_leaf_records = {}  # seg_id -> (m_sha, wid, layout_count)

        for wid in sorted(batch_obs_by_world.keys()):
            raw_list = batch_layouts_by_world[wid]
            # Canonical sort order: world_id/side/anchor/layout
            sorted_layouts = sorted(raw_list, key=lambda item: _layout_sort_key(item[0]))

            # Chunk into leaf_entries slices
            world_leaves = []
            for i in range(0, len(sorted_layouts), self.leaf_entries):
                chunk = sorted_layouts[i : i + self.leaf_entries]
                from .index import build_index
                index_manifest=self.artifacts.put_json(build_index([item[0] for item in chunk]))
                new_artifacts[index_manifest['sha256']]=index_manifest
                leaf_payload = {
                    "kind": "leaf",
                    "revision": "catalog-segment-leaf-v1",
                    "index_manifest": index_manifest,
                    "world_id": wid,
                    "layout_count": len(chunk),
                    "layouts": [
                        {
                            "revision": s["revision"],
                            "observation_id": s["observation_id"],
                            "world_id": s["world_id"],
                            "layout_id": s["layout_id"],
                            "seed": s["seed"],
                            "anchor": s["anchor"],
                            "border_side": s["border_side"],
                            "payload_sha256": bhash,
                            "payload_b64": b64,
                        }
                        for s, packed, bhash, b64 in chunk
                    ],
                }
                leaf_bytes = json.dumps(
                    leaf_payload, sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode("utf-8")
                if len(leaf_bytes) > 1024 * 1024:
                    raise ValueError("Leaf manifest uncompressed size exceeds 1MiB")
                if len(chunk) > self.leaf_entries:
                    raise ValueError(f"Leaf entries {len(chunk)} exceeds leaf_entries {self.leaf_entries}")

                leaf_m = self.artifacts.put_json(leaf_payload)
                seg_id = leaf_m["sha256"]
                new_artifacts[leaf_m["sha256"]] = leaf_m

                item = {
                    "kind": "leaf",
                    "sha256": leaf_m["sha256"],
                    "relative_key": leaf_m["relative_key"],
                    "byte_length": leaf_m["byte_length"],
                    "uncompressed_length": leaf_m["uncompressed_length"],
                    "codec": leaf_m["codec"],
                    "segment_id": seg_id,
                    "world_id": wid,
                    "layout_count": len(chunk),
                }
                world_leaves.append(item)
                new_leaf_records[seg_id] = (leaf_m["sha256"], wid, len(chunk))

            new_leaf_items[wid] = world_leaves

        # Assemble all leaf items in canonical order
        all_leaf_items = []
        for wid in sorted(all_worlds):
            if wid in new_leaf_items:
                all_leaf_items.extend(new_leaf_items[wid])
            else:
                all_leaf_items.extend(parent_leaf_items[wid])

        total_layouts = sum(item["layout_count"] for item in all_leaf_items)

        # Build content-addressed tree over leaves
        tree_root_manifest = self._build_tree(all_leaf_items, new_artifacts)

        # Snapshot root descriptor binding
        snapshot_descriptor = {
            "schema_revision": SCHEMA_REVISION,
            "parent_snapshot_id": parent,
            "tree_root_sha256": tree_root_manifest["sha256"],
            "header": current_header,
            "registry_revision": registry.REGISTRY_REVISION,
            "geometry_revision": models.GEOMETRY_REVISION,
            "summary_revision": models.SUMMARY_REVISION,
            "score_revision": registry.POLICY["score"]["revision"],
            "policy_sha256": registry.digest(registry.POLICY),
            "fanout": self.fanout,
            "leaf_entries": self.leaf_entries,
            "world_count": len(all_worlds),
            "layout_count": total_layouts,
        }
        snapshot_id = registry.digest(snapshot_descriptor)

        # Check for idempotent replay
        with self._lock:
            cur = self.conn.cursor()
            cur.execute("SELECT snapshot_id FROM snapshot_root WHERE snapshot_id = ?;", (snapshot_id,))
            if cur.fetchone():
                self.info(snapshot_id)
                return snapshot_id

        # Write root manifest artifact
        snap_payload = dict(snapshot_descriptor, snapshot_id=snapshot_id)
        snap_manifest = self.artifacts.put_json(snap_payload)
        new_artifacts[snap_manifest["sha256"]] = snap_manifest

        # Prepare observation refs for all worlds in this generation
        generation_obs_refs = []
        for wid in sorted(all_worlds):
            if wid in batch_obs_by_world:
                obs = batch_obs_by_world[wid]
                oid = models.observation_id(obs)
                seed_str = obs["identity"]["seed"]
                m = batch_obs_manifests[oid]
                generation_obs_refs.append((snapshot_id, wid, oid, seed_str, m["sha256"]))
            else:
                p_ref = parent_obs_refs[wid]
                generation_obs_refs.append(
                    (snapshot_id, wid, p_ref["observation_id"], p_ref["seed"], p_ref["manifest_sha256"])
                )

        now = datetime.now(timezone.utc).isoformat()

        # Single atomic metadata transaction
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            try:
                # Insert artifact refs
                for m in new_artifacts.values():
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO artifact_ref
                        (sha256, relative_key, byte_length, uncompressed_length, codec, published_at)
                        VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (m["sha256"], m["relative_key"], m["byte_length"], m["uncompressed_length"], m["codec"], now),
                    )

                # Insert leaf segments
                for seg_id, (m_sha, wid, l_cnt) in new_leaf_records.items():
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO leaf_segment
                        (segment_id, manifest_sha256, world_id, layout_count, created_at)
                        VALUES (?, ?, ?, ?, ?);
                        """,
                        (seg_id, m_sha, wid, l_cnt, now),
                    )

                # Insert snapshot root
                header_json_str = json.dumps(current_header, sort_keys=True, separators=(",", ":"))
                cursor.execute(
                    """
                    INSERT INTO snapshot_root
                    (snapshot_id, parent_id, manifest_sha256, tree_root_sha256, header_json, world_count, layout_count, published_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        snapshot_id,
                        parent,
                        snap_manifest["sha256"],
                        tree_root_manifest["sha256"],
                        header_json_str,
                        len(all_worlds),
                        total_layouts,
                        now,
                    ),
                )

                # Insert observation refs
                cursor.executemany(
                    """
                    INSERT INTO observation_ref
                    (snapshot_id, world_id, observation_id, seed, manifest_sha256)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    generation_obs_refs,
                )

                # Insert snapshot membership
                membership_rows = [
                    (snapshot_id, item["segment_id"], ordinal)
                    for ordinal, item in enumerate(all_leaf_items)
                ]
                cursor.executemany(
                    """
                    INSERT INTO snapshot_membership
                    (snapshot_id, segment_id, ordinal)
                    VALUES (?, ?, ?);
                    """,
                    membership_rows,
                )

                if prepare_publication is not None:
                    prepare_publication(self, snapshot_id)
                cursor.execute("COMMIT;")
            except Exception:
                cursor.execute("ROLLBACK;")
                raise

        return snapshot_id

    def snapshots(self) -> list[dict]:
        """List all published snapshots in creation order."""
        self._check_open()
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT snapshot_id, world_count, layout_count, header_json
                FROM snapshot_root
                ORDER BY rowid ASC;
                """
            )
            rows = cur.fetchall()
            return [
                {
                    "snapshot_id": r[0],
                    "worlds": r[1],
                    "layouts": r[2],
                    "header": json.loads(r[3]),
                }
                for r in rows
            ]

    def info(self, snapshot_id: str | None = None) -> dict:
        """Get summary info for snapshot (latest if snapshot_id is None)."""
        self._check_open()
        with self._lock:
            cur = self.conn.cursor()
            if snapshot_id is None:
                cur.execute(
                    """
                    SELECT snapshot_id, world_count, layout_count, header_json
                    FROM snapshot_root
                    ORDER BY rowid DESC
                    LIMIT 1;
                    """
                )
            else:
                if not isinstance(snapshot_id, str) or not _HEX64_RE.fullmatch(snapshot_id):
                    raise ValueError(f"Invalid snapshot_id: {snapshot_id}")
                cur.execute(
                    """
                    SELECT snapshot_id, world_count, layout_count, header_json
                    FROM snapshot_root
                    WHERE snapshot_id = ?;
                    """,
                    (snapshot_id,),
                )
            row = cur.fetchone()
            if not row:
                if snapshot_id is None:
                    raise ValueError("No snapshots exist in catalog")
                raise ValueError(f"Snapshot not found: {snapshot_id}")
            return {
                "snapshot_id": row[0],
                "worlds": row[1],
                "layouts": row[2],
                "header": json.loads(row[3]),
            }

    def iter_segments(self, snapshot_id: str | None = None, *, request=None, layout_key=None):
        """Stream read leaf segments with fully validated summary dicts."""
        self._check_open()
        if request is not None:
            from .request import load_request, validate_request
            request = load_request(request) if isinstance(request, str) else validate_request(request)
        if layout_key is not None and (not isinstance(layout_key,tuple) or len(layout_key)!=2 or
            any(not isinstance(value,str) or not _HEX64_RE.fullmatch(value) for value in layout_key)):
            raise ValueError('Invalid exact layout key')
        resolved_info = self.info(snapshot_id)
        sid = resolved_info["snapshot_id"]

        leaf_rows=self._verified_membership(sid)
        obs_refs={r[0]:(r[1],r[2]) for r in self.conn.execute('SELECT world_id,observation_id,seed FROM observation_ref WHERE snapshot_id=?',(sid,))}
        seen=set()
        world_ids_by_seed={}

        for seg_id, sha, rk, bl, ul, codec_name in leaf_rows:
            manifest = {
                "sha256": sha,
                "relative_key": rk,
                "byte_length": bl,
                "uncompressed_length": ul,
                "codec": codec_name,
            }
            leaf_json = self.artifacts.get_json(manifest)
            if leaf_json.get("kind") != "leaf" or leaf_json.get("revision") != "catalog-segment-leaf-v1":
                raise ValueError(f"Corrupt leaf manifest {seg_id}: invalid kind or revision")

            raw_layouts = leaf_json.get("layouts")
            if not isinstance(raw_layouts, list) or len(raw_layouts) > self.leaf_entries:
                raise ValueError(f"Corrupt leaf manifest {seg_id}: invalid layout count")

            if len(registry.canonical_json(leaf_json))>1<<20 or leaf_json.get('layout_count')!=len(raw_layouts):
                raise ValueError('Invalid leaf byte/count limit')
            index=None
            selected=range(len(raw_layouts))
            if leaf_json.get('index_manifest') is not None:
                from .index import validate_index,_select_index,INDEX_REVISION
                index=self.artifacts.get_json(leaf_json['index_manifest'])
                validate_index(index)
                # Recompute row ordering/content binding from saved metadata and
                # payload hashes, without unpacking every nonmatching row.
                entries=[dict(metadata={k:item[k] for k in ('revision','observation_id','world_id','layout_id','seed','anchor','border_side')},
                              payload_sha256=item['payload_sha256']) for item in raw_layouts]
                expected=registry.digest(dict(geometry_revision=models.GEOMETRY_REVISION,index_revision=INDEX_REVISION,
                    layouts=entries,policy_revision=registry.digest(registry.POLICY),registry_revision=registry.REGISTRY_REVISION))
                if index['content_digest']!=expected or index['num_rows']!=len(raw_layouts):raise ValueError('Leaf index row/content mismatch')
                # The index and request are already fully validated here. Public
                # filter_index keeps its independent validation boundary.
                if request is not None:selected=_select_index(index,request)
            if layout_key is not None:
                selected=[i for i in selected if (raw_layouts[i]['world_id'],raw_layouts[i]['layout_id'])==layout_key]
            decoded_layouts = []
            for position in selected:
                item=raw_layouts[position]
                if obs_refs.get(item['world_id'])!=(item['observation_id'],item['seed']):
                    raise ValueError('Layout/observation membership identity mismatch')
                # The header is fixed for this iterator. Reuse only its derived
                # world identity for identical, membership-checked seed strings.
                seed=item['seed']
                if seed not in world_ids_by_seed:
                    world_ids_by_seed[seed]=models.world_id(dict(resolved_info['header'],seed=seed))
                if world_ids_by_seed[seed]!=item['world_id']:
                    raise ValueError('Layout/build identity mismatch')
                geometry_key=(item['world_id'],item['border_side'],*item['anchor'])
                if geometry_key in seen:raise ValueError('Duplicate geometry across snapshot leaves')
                seen.add(geometry_key)
                b64_payload = item["payload_b64"]
                try:
                    packed_blob = base64.b64decode(b64_payload,validate=True)
                except Exception as exc:
                    raise ValueError(f"Corrupt layout base64 payload in {seg_id}: {exc}") from exc

                if len(packed_blob) != 364:
                    raise ValueError(f"Corrupt layout blob length in {seg_id}: {len(packed_blob)}")
                actual_sha = hashlib.sha256(packed_blob).hexdigest()
                if actual_sha != item["payload_sha256"]:
                    raise ValueError(f"Corrupt layout payload sha in {seg_id}")

                metadata = {
                    "revision": item["revision"],
                    "observation_id": item["observation_id"],
                    "world_id": item["world_id"],
                    "layout_id": item["layout_id"],
                    "seed": item["seed"],
                    "anchor": item["anchor"],
                    "border_side": item["border_side"],
                }
                if metadata["revision"] != models.SUMMARY_REVISION:
                    raise ValueError(f"Incompatible summary revision in layout {item['layout_id']}")

                summary = codec.unpack_summary(packed_blob, metadata)
                # unpack_summary validates the schema, numeric payload and the
                # layout ID derived from observation, anchor and border side.
                decoded_layouts.append(summary)

            yield {"segment_id":seg_id,"layouts":decoded_layouts,"index":index,
                   "total_rows":len(raw_layouts),"prefiltered":request is not None and index is not None}

    def identities(self, snapshot_id: str | None = None) -> list[dict]:
        """Derive pinned manifest metadata for all worlds in canonical order."""
        self._check_open()
        resolved_info = self.info(snapshot_id)
        sid = resolved_info["snapshot_id"]
        header = resolved_info["header"]

        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT world_id, seed
                FROM observation_ref
                WHERE snapshot_id = ?
                ORDER BY world_id ASC;
                """,
                (sid,),
            )
            rows = cur.fetchall()

        identities = []
        for wid, seed_str in rows:
            ident = dict(header, seed=seed_str)
            models.validate_identity(ident)
            actual_wid = models.world_id(ident)
            if actual_wid != wid:
                raise ValueError(f"Corrupt identity: world_id mismatch for seed {seed_str}")
            identities.append(ident)
        return identities

    def observation(self, snapshot_id: str, world_id: str) -> dict:
        """Lazy retrieval of raw observation proving generation membership."""
        self._check_open()
        if not isinstance(snapshot_id, str) or not _HEX64_RE.fullmatch(snapshot_id):
            raise KeyError(f"Invalid snapshot_id: {snapshot_id}")
        if not isinstance(world_id, str) or not _HEX64_RE.fullmatch(world_id):
            raise KeyError(f"Invalid world_id: {world_id}")

        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT o.observation_id, ar.sha256, ar.relative_key, ar.byte_length, ar.uncompressed_length, ar.codec
                FROM observation_ref o
                JOIN artifact_ref ar ON o.manifest_sha256 = ar.sha256
                WHERE o.snapshot_id = ? AND o.world_id = ?;
                """,
                (snapshot_id, world_id),
            )
            row = cur.fetchone()
            if not row:
                raise KeyError(f"World {world_id} not found in snapshot {snapshot_id}")

        oid, sha, rk, bl, ul, codec_name = row
        manifest = {
            "sha256": sha,
            "relative_key": rk,
            "byte_length": bl,
            "uncompressed_length": ul,
            "codec": codec_name,
        }
        obs = self.artifacts.get_json(manifest)
        models.validate_observation(obs)
        expected_header=self.info(snapshot_id)['header']
        if {k:v for k,v in obs['identity'].items() if k!='seed'}!=expected_header:
            raise ValueError('Observation build/header mismatch')
        if models.world_id(obs["identity"]) != world_id:
            raise ValueError(f"Observation world_id mismatch for world {world_id}")
        if models.observation_id(obs) != oid:
            raise ValueError(f"Observation ID mismatch: expected {oid}, got {models.observation_id(obs)}")
        return obs

    def audit(self, snapshot_id: str | None = None) -> dict:
        """Full reachability, raw observation validation and layout binding audit."""
        self._check_open()
        resolved_info = self.info(snapshot_id)
        sid = resolved_info["snapshot_id"]

        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT manifest_sha256, tree_root_sha256, header_json, world_count, layout_count
                FROM snapshot_root
                WHERE snapshot_id = ?;
                """,
                (sid,),
            )
            snap_row = cur.fetchone()
            if not snap_row:
                raise ValueError(f"Snapshot not found: {sid}")

            manifest_sha, tree_root_sha, header_json_str, expected_worlds, expected_layouts = snap_row
            cur.execute("SELECT relative_key, byte_length, uncompressed_length, codec FROM artifact_ref WHERE sha256 = ?;", (manifest_sha,))
            art_row = cur.fetchone()
            if not art_row:
                raise ValueError("Corrupt snapshot: missing root manifest artifact record")
            snap_manifest = {
                "sha256": manifest_sha,
                "relative_key": art_row[0],
                "byte_length": art_row[1],
                "uncompressed_length": art_row[2],
                "codec": art_row[3],
            }

            cur.execute("SELECT relative_key, byte_length, uncompressed_length, codec FROM artifact_ref WHERE sha256 = ?;", (tree_root_sha,))
            tree_art_row = cur.fetchone()
            if not tree_art_row:
                raise ValueError("Corrupt snapshot: missing tree root artifact record")
            tree_root_manifest = {
                "sha256": tree_root_sha,
                "relative_key": tree_art_row[0],
                "byte_length": tree_art_row[1],
                "uncompressed_length": tree_art_row[2],
                "codec": tree_art_row[3],
            }

        root_payload = self.artifacts.get_json(snap_manifest)
        if root_payload.get("snapshot_id") != sid:
            raise ValueError("Root manifest descriptor snapshot_id mismatch")
        if (
            root_payload.get("registry_revision") != registry.REGISTRY_REVISION
            or root_payload.get("geometry_revision") != models.GEOMETRY_REVISION
            or root_payload.get("summary_revision") != models.SUMMARY_REVISION
            or root_payload.get("score_revision") != registry.POLICY["score"]["revision"]
        ):
            raise ValueError("Incompatible revisions in snapshot root manifest")
        if root_payload.get("policy_sha256") != registry.digest(registry.POLICY):
            raise ValueError("Policy sha256 mismatch in snapshot root manifest")
        if root_payload.get("tree_root_sha256") != tree_root_sha:
            raise ValueError("Tree root sha256 mismatch in root manifest")

        header = json.loads(header_json_str)
        if root_payload.get("header") != header:
            raise ValueError("Header mismatch in root manifest")

        if registry.digest({k:v for k,v in root_payload.items() if k!='snapshot_id'})!=sid:
            raise ValueError('Root descriptor identity mismatch')

        # Walk tree and verify reachability of all leaves
        reachable_leaf_manifests = self._collect_leaf_manifests_from_tree(tree_root_manifest)

        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT sm.segment_id, ar.sha256, ar.relative_key, ar.byte_length, ar.uncompressed_length, ar.codec
                FROM snapshot_membership sm
                JOIN leaf_segment ls ON sm.segment_id = ls.segment_id
                JOIN artifact_ref ar ON ls.manifest_sha256 = ar.sha256
                WHERE sm.snapshot_id = ?
                ORDER BY sm.ordinal ASC;
                """,
                (sid,),
            )
            membership_rows = cur.fetchall()

        if len(reachable_leaf_manifests) != len(membership_rows):
            raise ValueError(
                f"Tree leaf count mismatch: reachable {len(reachable_leaf_manifests)}, membership {len(membership_rows)}"
            )

        for reachable_m, mem_row in zip(reachable_leaf_manifests, membership_rows):
            if reachable_m["sha256"] != mem_row[1]:
                raise ValueError("Tree reachable leaf does not match snapshot membership order")

        # Validate all layouts from iter_segments
        total_layouts = 0
        seen_lids = set()
        seen_worlds = set()

        for segment in self.iter_segments(sid):
            for summary in segment["layouts"]:
                lid = summary["layout_id"]
                if lid in seen_lids:
                    raise ValueError(f"Duplicate layout {lid} across snapshot segments")
                seen_lids.add(lid)
                seen_worlds.add(summary["world_id"])
                total_layouts += 1

        if total_layouts != expected_layouts or total_layouts != root_payload.get("layout_count"):
            raise ValueError(f"Layout count mismatch: expected {expected_layouts}, found {total_layouts}")

        # Validate all observations in snapshot
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT world_id, observation_id, seed
                FROM observation_ref
                WHERE snapshot_id = ?
                ORDER BY world_id ASC;
                """,
                (sid,),
            )
            obs_rows = cur.fetchall()

        if len(obs_rows) != expected_worlds or len(obs_rows) != root_payload.get("world_count"):
            raise ValueError(f"World count mismatch: expected {expected_worlds}, found {len(obs_rows)}")

        obs_world_ids = {r[0] for r in obs_rows}
        if seen_worlds != obs_world_ids:
            raise ValueError("Set of worlds in layouts does not match observation membership")

        for wid, oid, seed_str in obs_rows:
            obs = self.observation(sid, wid)
            if obs["identity"]["seed"] != seed_str:
                raise ValueError(f"Observation seed mismatch for world {wid}")
            obs_header = {k: v for k, v in sorted(obs["identity"].items()) if k != "seed"}
            if obs_header != header:
                raise ValueError(f"Observation header mismatch for world {wid}")

        return {
            "passed": True,
            "worlds": len(obs_rows),
            "layouts": total_layouts,
            "snapshot_id": sid,
        }

    def backup(self, destination: str | Path) -> None:
        """Create a consistent backup at a fresh destination and verify restored snapshots."""
        self._check_open()
        if not destination:
            raise ValueError("Destination must be provided")

        raw_dest = Path(destination)
        if raw_dest.is_symlink():
            raise ValueError(f"Destination cannot be a symlink: {destination}")

        curr = Path(raw_dest.parts[0]) if raw_dest.is_absolute() else Path(".")
        for part in raw_dest.parts[(1 if raw_dest.is_absolute() else 0):]:
            curr = curr / part
            if curr.is_symlink():
                raise ValueError(f"Symlink component detected in destination path: {curr}")

        dest = raw_dest.resolve()
        if raw_dest.is_symlink() or dest.is_symlink():
            raise ValueError(f"Destination cannot be a symlink: {destination}")

        if dest.exists() and any(dest.iterdir()):
            raise ValueError("Destination must be a fresh empty directory")
        dest.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink() or raw_dest.is_symlink():
            raise ValueError(f"Destination cannot be a symlink: {destination}")

        dest_db_path = dest / "pilot.sqlite"
        dest_conn = sqlite3.connect(str(dest_db_path), isolation_level=None)
        try:
            with self._lock:
                self.conn.backup(dest_conn)
        finally:
            dest_conn.close()

        # Copy all referenced artifacts safely
        dest_artifacts = ArtifactStore(dest / "artifacts")
        chk = sqlite3.connect(str(dest_db_path))
        try:
            artifacts = chk.execute(
                "SELECT sha256, relative_key, byte_length FROM artifact_ref;"
            ).fetchall()
            snapshot_ids = [
                r[0] for r in chk.execute("SELECT snapshot_id FROM snapshot_root;").fetchall()
            ]
        finally:
            chk.close()

        for sha, rk, bl in artifacts:
            self.artifacts.copy_raw_to(rk, dest_artifacts, expected_sha=sha, expected_len=bl)

        # Verify all restored snapshots using audit
        with SegmentedCatalog(dest) as restored:
            for sid in snapshot_ids:
                restored.audit(sid)
