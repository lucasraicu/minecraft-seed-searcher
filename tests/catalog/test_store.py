"""Tests for CatalogStore and ArtifactStore reference implementations."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import sqlite3
import threading
import time

import pytest

from seed_search.catalog.artifacts import ArtifactStore
from seed_search.catalog.store import CatalogStore, SCHEMA_REVISION
from seed_search.catalog import codec
from seed_search.catalog import geometry
from seed_search.catalog import models
from seed_search.catalog import registry


def make_synthetic_obs(seed="123456789", model_id="MC_26_50"):
    ident = models.identity(
        seed,
        model_id=model_id,
        native_sha256="a" * 64,
        source_sha256="b" * 64,
    )
    return models.empty_observation(ident)


def make_synthetic_summary(obs, anchor=(0, 0), border_side=2048):
    oid = models.observation_id(obs)
    wid = models.world_id(obs["identity"])
    lid = codec.layout_id(oid, anchor, border_side)
    summary = {
        "revision": models.SUMMARY_REVISION,
        "observation_id": oid,
        "world_id": wid,
        "layout_id": lid,
        "seed": obs["identity"]["seed"],
        "anchor": list(anchor),
        "border_side": border_side,
        "counts": [[0, 0, 0, 0] for _ in range(14)],
        "structure_nearest_d2": [codec.MISSING] * 14,
        "biome_nearest_d2": [codec.MISSING] * 9,
        "biome_witness_refs": [codec.MISSING] * 9,
        "complete": [[False, False, False, False] for _ in range(len(registry.FEATURE_IDS))],
    }
    return codec.validate_summary(summary)


def test_packpayload_metadata_roundtrip(tmp_path):
    # 1. ArtifactStore put_json / get_json roundtrip
    art_dir = tmp_path / "artifacts"
    store = ArtifactStore(art_dir)
    obs = make_synthetic_obs("987654321")
    manifest = store.put_json(obs)

    assert set(manifest.keys()) == {"sha256", "relative_key", "byte_length", "uncompressed_length", "codec"}
    assert manifest["codec"] == "gzip"
    assert manifest["sha256"] in manifest["relative_key"]
    assert manifest["byte_length"] > 0
    assert manifest["uncompressed_length"] > 0

    loaded_obs = store.get_json(manifest)
    assert loaded_obs == obs

    # 2. Codec 364-byte payload pack / unpack roundtrip
    summary = make_synthetic_summary(obs, anchor=(0, 0), border_side=2048)
    packed = codec.pack_summary(summary)
    assert isinstance(packed, bytes)
    assert len(packed) == 364

    meta = codec.summary_metadata(summary)
    unpacked = codec.unpack_summary(packed, meta)
    assert unpacked == summary

    # 3. CatalogStore publish and retrieval roundtrip
    cat_dir = tmp_path / "catalog"
    with CatalogStore(cat_dir) as cat:
        snap_id = cat.publish_snapshot([obs], [summary])
        assert isinstance(snap_id, str)
        assert len(snap_id) == 64

        retrieved = cat.snapshot(snap_id)
        assert retrieved["snapshot_id"] == snap_id
        assert len(retrieved["observations"]) == 1
        assert retrieved["observations"][0] == obs
        assert len(retrieved["layouts"]) == 1
        assert retrieved["layouts"][0] == summary


def test_corruption_incl_blobs(tmp_path):
    cat_dir = tmp_path / "catalog_corrupt"
    obs = make_synthetic_obs("1001")
    summary = make_synthetic_summary(obs, anchor=(256, 256), border_side=4096)

    with CatalogStore(cat_dir) as cat:
        snap_id = cat.publish_snapshot([obs], [summary])

        # Test A: Corrupt artifact file on disk
        # Find observation artifact file
        oid = models.observation_id(obs)
        cur = cat.conn.cursor()
        cur.execute("SELECT manifest_sha256 FROM observation_set WHERE observation_id = ?", (oid,))
        sha = cur.fetchone()[0]
        cur.execute("SELECT relative_key FROM artifact WHERE sha256 = ?", (sha,))
        rk = cur.fetchone()[0]

        art_file = cat.artifacts.root / rk
        assert art_file.exists()

        # Corrupt file content
        original_bytes = art_file.read_bytes()
        art_file.write_bytes(original_bytes[:-10] + b"CORRUPTED!")

        with pytest.raises(ValueError, match="sha256 mismatch|byte length mismatch"):
            cat.snapshot(snap_id)

        # Restore file content
        art_file.write_bytes(original_bytes)
        # Snapshot passes again
        cat.snapshot(snap_id)

        # Test B: Corrupt layout payload_blob in SQLite database
        lid = summary["layout_id"]
        corrupt_blob = b"\x00" * 364
        cur.execute("UPDATE layout SET payload_blob = ? WHERE layout_id = ?", (corrupt_blob, lid))
        cat.conn.commit()

        with pytest.raises(ValueError, match="Corrupt layout blob checksum"):
            cat.snapshot(snap_id)

        # Test C: Existing corrupt object in ArtifactStore.put_json
        art_store = cat.artifacts
        dummy_payload = {"test": 123}
        # Predict target key for dummy_payload
        uncomp = json.dumps(dummy_payload, sort_keys=True, separators=(",", ":")).encode()
        comp = gzip.compress(uncomp, compresslevel=9, mtime=0)
        d_sha = hashlib.sha256(comp).hexdigest()
        d_key = f"{d_sha[:2]}/{d_sha}.json.gz"
        d_path = art_store.root / d_key
        d_path.parent.mkdir(parents=True, exist_ok=True)
        d_path.write_bytes(b"CORRUPT_EXISTING_DATA")

        with pytest.raises(ValueError, match="Existing artifact.*is corrupt"):
            art_store.put_json(dummy_payload)


def test_traversal_and_symlink_escape(tmp_path):
    root = tmp_path / "safe_store"
    art_store = ArtifactStore(root)

    # Path traversal attempts
    with pytest.raises(ValueError, match="Path traversal|Absolute paths"):
        art_store._safe_resolve_key("../escape.json.gz")

    with pytest.raises(ValueError, match="Absolute paths"):
        art_store._safe_resolve_key("/etc/passwd")

    with pytest.raises(ValueError, match="opaque content-address key"):
        art_store._safe_resolve_key("arbitrary_name.json")

    # Symlink component inside root
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    symlink_dir = root / "12"
    symlink_dir.symlink_to(outside_dir, target_is_directory=True)

    test_key = "12/" + "a" * 64 + ".json.gz"
    with pytest.raises(ValueError, match="Symlink component detected"):
        art_store._safe_resolve_key(test_key)

    # Symlink root rejection
    symlink_root = tmp_path / "sym_root"
    symlink_root.symlink_to(root, target_is_directory=True)

    with pytest.raises(ValueError, match="Root cannot be a symlink|Root path cannot be a symlink"):
        ArtifactStore(symlink_root)

    with pytest.raises(ValueError, match="Root path cannot be a symlink"):
        CatalogStore(symlink_root)


def test_decompression_limits(tmp_path):
    small_limit = 512
    art_store = ArtifactStore(tmp_path / "small_store", max_bytes=small_limit)

    large_payload = {"big_data": "x" * (small_limit + 10)}
    with pytest.raises(ValueError, match="exceeds max_bytes"):
        art_store.put_json(large_payload)

    # Manifest claiming byte_length within max_bytes, but uncompressed_length exceeds limit
    bad_manifest = {
        "sha256": "0" * 64,
        "relative_key": "00/" + "0" * 64 + ".json.gz",
        "byte_length": 50,
        "uncompressed_length": 1000,
        "codec": "gzip",
    }
    with pytest.raises(ValueError, match="Invalid uncompressed_length in manifest"):
        art_store.get_json(bad_manifest)

    # Decompression limit triggered during actual streaming decompression (zip bomb)
    # Compressed size is small (e.g. 50 bytes), but decompresses to 2000 bytes
    bomb_raw = json.dumps({"payload": "a" * 2000}).encode()
    bomb_comp = gzip.compress(bomb_raw, compresslevel=9, mtime=0)
    bomb_sha = hashlib.sha256(bomb_comp).hexdigest()
    bomb_key = f"{bomb_sha[:2]}/{bomb_sha}.json.gz"
    bomb_path = art_store.root / bomb_key
    bomb_path.parent.mkdir(parents=True, exist_ok=True)
    bomb_path.write_bytes(bomb_comp)

    # Manifest deceptively claiming uncompressed_length is within limit (e.g. 300)
    bomb_manifest = {
        "sha256": bomb_sha,
        "relative_key": bomb_key,
        "byte_length": len(bomb_comp),
        "uncompressed_length": 300,
        "codec": "gzip",
    }
    with pytest.raises(ValueError, match="Decompressed payload exceeds max_bytes limit"):
        art_store.get_json(bomb_manifest)


def test_repeated_publish_and_immutability(tmp_path):
    cat_dir = tmp_path / "cat_replay"
    obs1 = make_synthetic_obs("2001")
    sum1 = make_synthetic_summary(obs1, anchor=(0, 0), border_side=2048)

    with CatalogStore(cat_dir) as cat:
        snap_id_1 = cat.publish_snapshot([obs1], [sum1])
        # Idempotent replay of identical snapshot
        snap_id_2 = cat.publish_snapshot([obs1], [sum1])
        assert snap_id_1 == snap_id_2

        # Conflict: Try publishing another observation with same observation_id but conflicting data
        # Note: changing seed or native_sha256 changes observation_id, but if observation_id is identical:
        # If we alter obs1 data without changing ID (by creating obs2 with identical identity but altered metrics)
        obs_conflict = make_synthetic_obs("2001")
        obs_conflict["metrics"]["rogue"] = 999
        # Both obs1 and obs_conflict have same observation_id? No, digest(obs) includes metrics!
        # What if obs_conflict has different observation_id? Then it's a new observation.
        # But what if we simulate an immutability conflict in the DB for the same observation_id:
        cur = cat.conn.cursor()
        cur.execute("SELECT manifest_sha256 FROM observation_set WHERE observation_id = ?", (models.observation_id(obs1),))
        # Modify DB artifact record to point to different data
        other_obs = make_synthetic_obs("2002")
        other_m = cat.artifacts.put_json(other_obs)
        cur.execute(
            "INSERT INTO artifact (sha256, relative_key, byte_length, uncompressed_length, codec, published_at) VALUES (?, ?, ?, ?, ?, ?);",
            (other_m["sha256"], other_m["relative_key"], other_m["byte_length"], other_m["uncompressed_length"], other_m["codec"], "now")
        )
        cur.execute("UPDATE observation_set SET manifest_sha256 = ? WHERE observation_id = ?", (other_m["sha256"], models.observation_id(obs1)))
        cat.conn.commit()

        with pytest.raises(ValueError, match="Conflict: observation.*already exists with different data"):
            cat.publish_snapshot([obs1], [sum1])

        # Duplicate observation in single batch
        with pytest.raises(ValueError, match="Duplicate observation"):
            cat.publish_snapshot([obs1, obs1], [sum1])

        # Duplicate layout in single batch
        with pytest.raises(ValueError, match="Duplicate layout"):
            cat.publish_snapshot([obs1], [sum1, sum1])


def test_rollback_and_fault_injection(tmp_path):
    cat_dir = tmp_path / "cat_rollback"
    obs = make_synthetic_obs("3001")
    summary = make_synthetic_summary(obs)

    with CatalogStore(cat_dir) as cat:
        # Fault injection via SQLite trigger to abort during transaction
        cat.conn.execute(
            "CREATE TRIGGER fault_inject BEFORE INSERT ON catalog_snapshot "
            "BEGIN SELECT RAISE(ABORT, 'Fault injection: aborted insert'); END;"
        )

        with pytest.raises(sqlite3.IntegrityError, match="Fault injection: aborted insert"):
            cat.publish_snapshot([obs], [summary])

        # Remove fault trigger
        cat.conn.execute("DROP TRIGGER fault_inject;")

        # Verify database has no half-published snapshot
        cur = cat.conn.cursor()
        assert cur.execute("SELECT COUNT(*) FROM catalog_snapshot;").fetchone()[0] == 0
        assert cur.execute("SELECT COUNT(*) FROM snapshot_observation;").fetchone()[0] == 0
        assert cur.execute("SELECT COUNT(*) FROM snapshot_layout;").fetchone()[0] == 0

        # Successful publish now works
        snap_id = cat.publish_snapshot([obs], [summary])
        assert isinstance(snap_id, str)
        assert cur.execute("SELECT COUNT(*) FROM catalog_snapshot;").fetchone()[0] == 1


def test_unknown_snapshot(tmp_path):
    cat_dir = tmp_path / "cat_unknown"
    with CatalogStore(cat_dir) as cat:
        with pytest.raises(KeyError, match="Unknown snapshot"):
            cat.snapshot("0" * 64)

        with pytest.raises(KeyError, match="Invalid or unknown"):
            cat.snapshot("invalid_non_hex")


def test_backup_and_restore(tmp_path):
    src_dir = tmp_path / "src_catalog"
    obs = make_synthetic_obs("4001")
    summary = make_synthetic_summary(obs)

    with CatalogStore(src_dir) as src_cat:
        snap_id = src_cat.publish_snapshot([obs], [summary])

        # Destination must be fresh
        non_fresh_dest = tmp_path / "non_fresh"
        non_fresh_dest.mkdir()
        (non_fresh_dest / "junk.txt").write_text("existing")

        with pytest.raises(ValueError, match="Destination must be a fresh empty directory"):
            src_cat.backup(non_fresh_dest)

        # Destination symlink rejected
        symlink_dest = tmp_path / "sym_dest"
        symlink_dest.symlink_to(non_fresh_dest, target_is_directory=True)
        with pytest.raises(ValueError, match="Destination cannot be a symlink"):
            src_cat.backup(symlink_dest)

        # Safe backup to fresh destination
        backup_dest = tmp_path / "backup_dest"
        src_cat.backup(backup_dest)

    # Open restored store and verify snapshot
    with CatalogStore(backup_dest) as restored_cat:
        snap = restored_cat.snapshot(snap_id)
        assert snap["snapshot_id"] == snap_id
        assert len(snap["observations"]) == 1
        assert snap["observations"][0] == obs
        assert len(snap["layouts"]) == 1
        assert snap["layouts"][0] == summary


def test_reader_consistency(tmp_path):
    cat_dir = tmp_path / "cat_readers"
    obs = make_synthetic_obs("5001")
    summary = make_synthetic_summary(obs)

    with CatalogStore(cat_dir) as writer_cat:
        reader_cat = CatalogStore(cat_dir)

        # Calculate what snapshot_id will be
        oid = models.observation_id(obs)
        lid = summary["layout_id"]
        snap_id = registry.digest({
            "geometry_revision": models.GEOMETRY_REVISION,
            "layout_digests": [lid],
            "layout_payload_sha256": {lid: hashlib.sha256(codec.pack_summary(summary)).hexdigest()},
            "observation_digests": [oid],
            "registry_revision": registry.REGISTRY_REVISION,
            "summary_revision": models.SUMMARY_REVISION,
            "score_revision": registry.POLICY['score']['revision'],
            "policy_sha256": registry.digest(registry.POLICY),
        })

        # Before publish: reader must see KeyError, never partial
        with pytest.raises(KeyError):
            reader_cat.snapshot(snap_id)

        # Publish in writer
        writer_cat.publish_snapshot([obs], [summary])

        # After publish: reader sees consistent snapshot immediately
        snap = reader_cat.snapshot(snap_id)
        assert snap["snapshot_id"] == snap_id
        assert snap["observations"][0] == obs
        assert snap["layouts"][0] == summary

        reader_cat.close()


def test_identity_mismatch(tmp_path):
    cat_dir = tmp_path / "cat_identity"
    obs1 = make_synthetic_obs("6001")
    obs2 = make_synthetic_obs("6002")

    with CatalogStore(cat_dir) as cat:
        # Layout references observation_id not supplied in batch
        summary_unbound = make_synthetic_summary(obs2)
        with pytest.raises(ValueError, match="references observation_id.*not in supplied"):
            cat.publish_snapshot([obs1], [summary_unbound])

        # Layout seed mismatch
        summary_bad_seed = make_synthetic_summary(obs1)
        summary_bad_seed["seed"] = "999999999"
        # validate_summary rejects this or publish_snapshot rejects this
        with pytest.raises(ValueError):
            cat.publish_snapshot([obs1], [summary_bad_seed])

        # Layout world_id mismatch
        summary_bad_wid = make_synthetic_summary(obs1)
        summary_bad_wid["world_id"] = "f" * 64
        with pytest.raises(ValueError, match="world_id does not match"):
            cat.publish_snapshot([obs1], [summary_bad_wid])

        # Layout anchor invalid
        summary_bad_anchor = make_synthetic_summary(obs1)
        summary_bad_anchor["anchor"] = [1, 2]
        with pytest.raises(ValueError):
            cat.publish_snapshot([obs1], [summary_bad_anchor])


def test_strict_json_rejection(tmp_path):
    art_store = ArtifactStore(tmp_path / "json_rejection")

    # Non-finite JSON rejection in put_json
    with pytest.raises(ValueError, match="Non-JSON or nonfinite payload"):
        art_store.put_json({"inf": float("inf")})

    with pytest.raises(ValueError, match="Non-JSON or nonfinite payload"):
        art_store.put_json({"nan": float("nan")})

    # Duplicate JSON key rejection in get_json
    raw_dup_json = b'{"key": 1, "key": 2}'
    comp = gzip.compress(raw_dup_json, compresslevel=9, mtime=0)
    sha = hashlib.sha256(comp).hexdigest()
    rk = f"{sha[:2]}/{sha}.json.gz"
    path = art_store.root / rk
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(comp)

    manifest = {
        "sha256": sha,
        "relative_key": rk,
        "byte_length": len(comp),
        "uncompressed_length": len(raw_dup_json),
        "codec": "gzip",
    }
    with pytest.raises(ValueError, match="Duplicate JSON key"):
        art_store.get_json(manifest)


def test_personal_database_reuse_prevention(tmp_path):
    # Case 1: Forbidden personal DB file in root
    root1 = tmp_path / "reuse1"
    root1.mkdir()
    (root1 / "seeds.db").write_text("personal DB")
    with pytest.raises(ValueError, match="Personal database file.*detected"):
        CatalogStore(root1)

    # Case 2: Forbidden personal DB tables in catalog.sqlite
    root2 = tmp_path / "reuse2"
    root2.mkdir()
    conn = sqlite3.connect(str(root2 / "catalog.sqlite"))
    conn.execute("CREATE TABLE personal_policy (id INT PRIMARY KEY);")
    conn.close()

    with pytest.raises(ValueError, match="Personal database schema detected"):
        CatalogStore(root2)

    # Case 3: Missing schema_meta marker in existing sqlite DB
    root3 = tmp_path / "reuse3"
    root3.mkdir()
    conn = sqlite3.connect(str(root3 / "catalog.sqlite"))
    conn.execute("CREATE TABLE random_table (x INT);")
    conn.close()

    with pytest.raises(ValueError, match="missing schema_meta marker"):
        CatalogStore(root3)
