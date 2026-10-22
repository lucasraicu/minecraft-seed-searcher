"""Comprehensive critical tests for SegmentedCatalog."""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import sqlite3

import pytest

from seed_search.catalog.artifacts import ArtifactStore
from seed_search.catalog.segments import SegmentedCatalog, SCHEMA_REVISION
from seed_search.catalog import codec
from seed_search.catalog import geometry
from seed_search.catalog import models
from seed_search.catalog import registry


def make_synthetic_obs(seed="123456789", model_id="MC_26_50", native_sha=None, source_sha=None):
    ident = models.identity(
        seed,
        model_id=model_id,
        native_sha256=native_sha or ("a" * 64),
        source_sha256=source_sha or ("b" * 64),
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


def test_basic_publish_and_iter_segments(tmp_path):
    cat_dir = tmp_path / "cat_basic"
    obs1 = make_synthetic_obs("10001")
    obs2 = make_synthetic_obs("10002")
    wid1 = models.world_id(obs1["identity"])
    wid2 = models.world_id(obs2["identity"])

    sum1_a = make_synthetic_summary(obs1, anchor=(0, 0), border_side=2048)
    sum1_b = make_synthetic_summary(obs1, anchor=(256, 256), border_side=4096)
    sum2_a = make_synthetic_summary(obs2, anchor=(0, 0), border_side=2048)

    with SegmentedCatalog(cat_dir) as cat:
        snap_id = cat.publish([obs1, obs2], [sum1_a, sum1_b, sum2_a])
        assert isinstance(snap_id, str)
        assert len(snap_id) == 64

        # Verify snapshots()
        snaps = cat.snapshots()
        assert len(snaps) == 1
        assert snaps[0]["snapshot_id"] == snap_id
        assert snaps[0]["worlds"] == 2
        assert snaps[0]["layouts"] == 3
        assert "seed" not in snaps[0]["header"]
        assert snaps[0]["header"]["model_id"] == "MC_26_50"

        # Verify info()
        info_latest = cat.info()
        assert info_latest == snaps[0]
        info_explicit = cat.info(snap_id)
        assert info_explicit == snaps[0]

        # Verify identities()
        idents = cat.identities(snap_id)
        assert len(idents) == 2
        # Canonical world ordering
        assert [models.world_id(i) for i in idents] == sorted([wid1, wid2])
        assert {i["seed"] for i in idents} == {"10001", "10002"}

        # Verify observation() lazy retrieval
        ret_obs1 = cat.observation(snap_id, wid1)
        assert ret_obs1 == obs1
        ret_obs2 = cat.observation(snap_id, wid2)
        assert ret_obs2 == obs2

        # Verify iter_segments()
        segments = list(cat.iter_segments(snap_id))
        # Default leaf_entries=256, each world has its own leaf
        assert len(segments) == 2
        all_unpacked = [lay for seg in segments for lay in seg["layouts"]]
        assert len(all_unpacked) == 3

        # Verify audit()
        audit_res = cat.audit(snap_id)
        assert audit_res["passed"] is True
        assert audit_res["worlds"] == 2
        assert audit_res["layouts"] == 3
        assert audit_res["snapshot_id"] == snap_id


def test_bounded_tree_and_fanout(tmp_path):
    cat_dir = tmp_path / "cat_tree"
    obs = make_synthetic_obs("20001")
    wid = models.world_id(obs["identity"])

    # Create 25 distinct layouts for one world
    anchors = geometry.anchors()[:25]
    layouts = [make_synthetic_summary(obs, anchor=a, border_side=2048) for a in anchors]

    # Use leaf_entries=5 and fanout=2 to force multi-level tree
    # 25 layouts with leaf_entries=5 -> 5 leaves
    # 5 leaves with fanout=2 -> Level 1 has 3 nodes (2, 2, 1) -> Level 2 has 2 nodes (2, 1) -> Level 3 root (2)
    with SegmentedCatalog(cat_dir, leaf_entries=5, fanout=2) as cat:
        snap_id = cat.publish([obs], layouts)
        assert isinstance(snap_id, str)

        segments = list(cat.iter_segments(snap_id))
        assert len(segments) == 5
        for seg in segments:
            assert len(seg["layouts"]) == 5

        # All 25 layouts decoded and in canonical order
        all_lids = [l["layout_id"] for seg in segments for l in seg["layouts"]]
        assert len(all_lids) == 25
        assert len(set(all_lids)) == 25

        audit_res = cat.audit(snap_id)
        assert audit_res["passed"] is True
        assert audit_res["worlds"] == 1
        assert audit_res["layouts"] == 25


def test_read_membership_and_lazy_obs(tmp_path):
    cat_dir = tmp_path / "cat_membership"
    obs1 = make_synthetic_obs("30001")
    obs2 = make_synthetic_obs("30002")
    obs3 = make_synthetic_obs("30003")
    wid1 = models.world_id(obs1["identity"])
    wid2 = models.world_id(obs2["identity"])
    wid3 = models.world_id(obs3["identity"])

    sum1 = make_synthetic_summary(obs1)
    sum2 = make_synthetic_summary(obs2)
    sum3 = make_synthetic_summary(obs3)

    with SegmentedCatalog(cat_dir) as cat:
        snap1 = cat.publish([obs1, obs2], [sum1, sum2])
        snap2 = cat.publish([obs3], [sum3], parent=snap1)

        # In snap1, wid1 and wid2 exist, wid3 does not
        assert cat.observation(snap1, wid1) == obs1
        assert cat.observation(snap1, wid2) == obs2
        with pytest.raises(KeyError, match="not found in snapshot"):
            cat.observation(snap1, wid3)

        # In snap2, wid1, wid2 and wid3 all exist
        assert cat.observation(snap2, wid1) == obs1
        assert cat.observation(snap2, wid2) == obs2
        assert cat.observation(snap2, wid3) == obs3

        # Nonexistent world ID raises KeyError
        with pytest.raises(KeyError):
            cat.observation(snap2, "f" * 64)


def test_raw_identity_and_uniform_header(tmp_path):
    cat_dir = tmp_path / "cat_header"
    obs1 = make_synthetic_obs("40001", model_id="MC_26_50")
    # Incompatible model_id creates non-uniform header
    obs_diff = make_synthetic_obs("40002", model_id="MC_26_50", native_sha="c" * 64)

    sum1 = make_synthetic_summary(obs1)
    sum_diff = make_synthetic_summary(obs_diff)

    with SegmentedCatalog(cat_dir) as cat:
        # Mixed header in batch rejected
        with pytest.raises(ValueError, match="Mixed build/settings identities"):
            cat.publish([obs1, obs_diff], [sum1, sum_diff])

        snap1 = cat.publish([obs1], [sum1])

        # Appending with incompatible header rejected
        with pytest.raises(ValueError, match="Incompatible header with parent"):
            cat.publish([obs_diff], [sum_diff], parent=snap1)


def test_canonical_generation_and_order_independence(tmp_path):
    cat_dir_a = tmp_path / "cat_order_a"
    cat_dir_b = tmp_path / "cat_order_b"

    obs1 = make_synthetic_obs("50001")
    obs2 = make_synthetic_obs("50002")
    obs3 = make_synthetic_obs("50003")

    sum1_a = make_synthetic_summary(obs1, anchor=(0, 0), border_side=2048)
    sum1_b = make_synthetic_summary(obs1, anchor=(512, 512), border_side=4096)
    sum2_a = make_synthetic_summary(obs2, anchor=(0, 0), border_side=2048)
    sum3_a = make_synthetic_summary(obs3, anchor=(-256, 0), border_side=8192)

    # Catalog A publishes in order [obs1, obs2, obs3] and layout order A
    with SegmentedCatalog(cat_dir_a) as cat_a:
        snap_a = cat_a.publish(
            [obs1, obs2, obs3],
            [sum1_a, sum1_b, sum2_a, sum3_a],
        )

    # Catalog B publishes in reversed/shuffled order [obs3, obs1, obs2] and reversed layouts
    with SegmentedCatalog(cat_dir_b) as cat_b:
        snap_b = cat_b.publish(
            [obs3, obs1, obs2],
            [sum3_a, sum2_a, sum1_b, sum1_a],
        )

    # Snapshot ID and content must be 100% deterministic and identical
    assert snap_a == snap_b


def test_replay_and_idempotency(tmp_path):
    cat_dir = tmp_path / "cat_replay"
    obs1 = make_synthetic_obs("60001")
    sum1 = make_synthetic_summary(obs1)

    obs2 = make_synthetic_obs("60002")
    sum2 = make_synthetic_summary(obs2)

    with SegmentedCatalog(cat_dir) as cat:
        snap1 = cat.publish([obs1], [sum1])
        # Idempotent replay of root publish
        snap1_repeat = cat.publish([obs1], [sum1])
        assert snap1 == snap1_repeat
        assert len(cat.snapshots()) == 1

        # Append to parent
        snap2 = cat.publish([obs2], [sum2], parent=snap1)
        assert snap2 != snap1

        # Idempotent replay of append
        snap2_repeat = cat.publish([obs2], [sum2], parent=snap1)
        assert snap2 == snap2_repeat
        assert len(cat.snapshots()) == 2

        # Old root snap1 remains readable and unchanged
        info1 = cat.info(snap1)
        assert info1["worlds"] == 1
        assert info1["layouts"] == 1
        cat.audit(snap1)


def test_conflict_and_replace_worlds(tmp_path):
    cat_dir = tmp_path / "cat_conflict"
    obs1 = make_synthetic_obs("70001")
    wid1 = models.world_id(obs1["identity"])
    sum1 = make_synthetic_summary(obs1, anchor=(0, 0), border_side=2048)

    with SegmentedCatalog(cat_dir) as cat:
        snap1 = cat.publish([obs1], [sum1])

        # New observation for wid1 (e.g. additional metrics or different layouts)
        obs1_updated = make_synthetic_obs("70001")
        obs1_updated["metrics"]["extra"] = 42
        sum1_updated = make_synthetic_summary(obs1_updated, anchor=(256, 256), border_side=4096)

        # Attempt to publish conflicting world without replace_worlds -> rejected
        with pytest.raises(ValueError, match="Conflict: world.*already exists.*replace_worlds"):
            cat.publish([obs1_updated], [sum1_updated], parent=snap1)

        # Invalid replace_worlds without parent -> rejected
        with pytest.raises(ValueError, match="replace_worlds cannot be specified without a parent"):
            cat.publish([obs1_updated], [sum1_updated], replace_worlds=[wid1])

        # replace_worlds with unknown world -> rejected
        with pytest.raises(ValueError, match="not present in parent snapshot"):
            cat.publish([obs1_updated], [sum1_updated], parent=snap1, replace_worlds=["e" * 64])

        # Authorized replacement with replace_worlds
        snap2 = cat.publish([obs1_updated], [sum1_updated], parent=snap1, replace_worlds=[wid1])
        assert snap2 != snap1

        # Snap1 preserves original observation and layout
        old_obs = cat.observation(snap1, wid1)
        assert "extra" not in old_obs["metrics"]
        old_segments = list(cat.iter_segments(snap1))
        assert old_segments[0]["layouts"][0]["border_side"] == 2048

        # Snap2 has updated observation and layout
        new_obs = cat.observation(snap2, wid1)
        assert new_obs["metrics"]["extra"] == 42
        new_segments = list(cat.iter_segments(snap2))
        assert new_segments[0]["layouts"][0]["border_side"] == 4096


def test_leaf_reuse_on_append(tmp_path):
    cat_dir = tmp_path / "cat_reuse"
    obs1 = make_synthetic_obs("80001")
    obs2 = make_synthetic_obs("80002")
    wid1 = models.world_id(obs1["identity"])
    wid2 = models.world_id(obs2["identity"])

    sum1 = make_synthetic_summary(obs1)
    sum2 = make_synthetic_summary(obs2)

    with SegmentedCatalog(cat_dir) as cat:
        snap1 = cat.publish([obs1], [sum1])
        # Find leaf segment for world 1 in snap1
        seg1 = list(cat.iter_segments(snap1))[0]["segment_id"]

        # Append world 2 to snap1
        snap2 = cat.publish([obs2], [sum2], parent=snap1)
        segments2 = list(cat.iter_segments(snap2))
        assert len(segments2) == 2

        # Unchanged world 1 reuses identical leaf segment
        seg2_ids = {s["segment_id"] for s in segments2}
        assert seg1 in seg2_ids


def test_backup_and_restore(tmp_path):
    src_dir = tmp_path / "cat_src"
    obs = make_synthetic_obs("90001")
    summary = make_synthetic_summary(obs)

    with SegmentedCatalog(src_dir) as src_cat:
        snap_id = src_cat.publish([obs], [summary])

        # Non-fresh destination rejected
        non_fresh = tmp_path / "non_fresh"
        non_fresh.mkdir()
        (non_fresh / "junk.txt").write_text("data")
        with pytest.raises(ValueError, match="fresh empty directory"):
            src_cat.backup(non_fresh)

        # Symlink destination rejected
        symlink_dest = tmp_path / "sym_dest"
        symlink_dest.symlink_to(non_fresh, target_is_directory=True)
        with pytest.raises(ValueError, match="Destination cannot be a symlink"):
            src_cat.backup(symlink_dest)

        # Valid backup
        dest_dir = tmp_path / "cat_dest"
        src_cat.backup(dest_dir)

    # Restored catalog passes audit and verifies
    with SegmentedCatalog(dest_dir) as restored_cat:
        audit_res = restored_cat.audit(snap_id)
        assert audit_res["passed"] is True
        assert audit_res["worlds"] == 1
        assert audit_res["layouts"] == 1
        assert restored_cat.observation(snap_id, models.world_id(obs["identity"])) == obs


def test_corruption_detection(tmp_path):
    cat_dir = tmp_path / "cat_corrupt"
    obs = make_synthetic_obs("100001")
    summary = make_synthetic_summary(obs)

    with SegmentedCatalog(cat_dir) as cat:
        snap_id = cat.publish([obs], [summary])

        # Test A: Corrupt leaf artifact file
        seg_id = list(cat.iter_segments(snap_id))[0]["segment_id"]
        cur = cat.conn.cursor()
        cur.execute("SELECT manifest_sha256 FROM leaf_segment WHERE segment_id = ?", (seg_id,))
        m_sha = cur.fetchone()[0]
        cur.execute("SELECT relative_key FROM artifact_ref WHERE sha256 = ?", (m_sha,))
        rk = cur.fetchone()[0]

        art_file = cat.artifacts.root / rk
        orig_bytes = art_file.read_bytes()
        art_file.write_bytes(orig_bytes[:-10] + b"CORRUPTED!")

        with pytest.raises(ValueError, match="sha256 mismatch|byte length mismatch"):
            list(cat.iter_segments(snap_id))

        with pytest.raises(ValueError):
            cat.audit(snap_id)

        # Restore file
        art_file.write_bytes(orig_bytes)
        cat.audit(snap_id)

        # Test B: Corrupt observation artifact
        cur.execute("SELECT manifest_sha256 FROM observation_ref WHERE snapshot_id = ?", (snap_id,))
        obs_sha = cur.fetchone()[0]
        cur.execute("SELECT relative_key FROM artifact_ref WHERE sha256 = ?", (obs_sha,))
        obs_rk = cur.fetchone()[0]
        obs_file = cat.artifacts.root / obs_rk
        orig_obs_bytes = obs_file.read_bytes()
        obs_file.write_bytes(orig_obs_bytes[:-10] + b"OBS_CORRUPT")

        with pytest.raises(ValueError):
            cat.observation(snap_id, models.world_id(obs["identity"]))

        obs_file.write_bytes(orig_obs_bytes)
        cat.audit(snap_id)

    # Test C: Forbidden database file in root
    f_dir = tmp_path / "forbidden_root"
    f_dir.mkdir()
    (f_dir / "catalog.sqlite").write_text("old db")
    with pytest.raises(ValueError, match="Forbidden database file.*detected"):
        SegmentedCatalog(f_dir)

    (f_dir / "catalog.sqlite").unlink()
    (f_dir / "seeds.db").write_text("personal db")
    with pytest.raises(ValueError, match="Forbidden database file.*detected"):
        SegmentedCatalog(f_dir)

    # Test D: Symlink database file
    sym_db_dir = tmp_path / "sym_db_dir"
    sym_db_dir.mkdir()
    target_sqlite = tmp_path / "target.sqlite"
    target_sqlite.touch()
    (sym_db_dir / "pilot.sqlite").symlink_to(target_sqlite)
    with pytest.raises(ValueError, match="Symlink database files are not allowed"):
        SegmentedCatalog(sym_db_dir)


def test_process_fault_and_rollback(tmp_path):
    cat_dir = tmp_path / "cat_fault"
    obs1 = make_synthetic_obs("110001")
    sum1 = make_synthetic_summary(obs1)

    obs2 = make_synthetic_obs("110002")
    sum2 = make_synthetic_summary(obs2)

    with SegmentedCatalog(cat_dir) as cat:
        snap1 = cat.publish([obs1], [sum1])

        # Inject SQLite trigger fault during publish transaction
        cat.conn.execute(
            "CREATE TRIGGER fault_inject BEFORE INSERT ON snapshot_root "
            "BEGIN SELECT RAISE(ABORT, 'Fault injection aborted'); END;"
        )

        with pytest.raises(sqlite3.IntegrityError, match="Fault injection aborted"):
            cat.publish([obs2], [sum2], parent=snap1)

        # Verify rollback: database still has exactly 1 snapshot
        cat.conn.execute("DROP TRIGGER fault_inject;")
        assert len(cat.snapshots()) == 1
        cat.audit(snap1)

        # Subsequent publish succeeds
        snap2 = cat.publish([obs2], [sum2], parent=snap1)
        assert len(cat.snapshots()) == 2
        cat.audit(snap2)


def test_reader_consistency(tmp_path):
    cat_dir = tmp_path / "cat_readers"
    obs = make_synthetic_obs("120001")
    summary = make_synthetic_summary(obs)

    with SegmentedCatalog(cat_dir) as writer:
        reader = SegmentedCatalog(cat_dir)

        # Before publish, reader sees no snapshots
        assert len(reader.snapshots()) == 0
        with pytest.raises(ValueError, match="No snapshots exist"):
            reader.info()

        snap_id = writer.publish([obs], [summary])

        # After publish, reader sees consistent snapshot immediately
        assert len(reader.snapshots()) == 1
        r_info = reader.info(snap_id)
        assert r_info["snapshot_id"] == snap_id
        audit_res = reader.audit(snap_id)
        assert audit_res["passed"] is True

        reader.close()


def test_context_manager_and_parameter_limits(tmp_path):
    root = tmp_path / "cat_params"

    # leaf_entries limits
    with pytest.raises(ValueError, match="leaf_entries must be an integer between 1 and 256"):
        SegmentedCatalog(root, leaf_entries=0)
    with pytest.raises(ValueError, match="leaf_entries must be an integer between 1 and 256"):
        SegmentedCatalog(root, leaf_entries=300)

    # fanout limits
    with pytest.raises(ValueError, match="fanout must be an integer between 2 and 128"):
        SegmentedCatalog(root, fanout=1)
    with pytest.raises(ValueError, match="fanout must be an integer between 2 and 128"):
        SegmentedCatalog(root, fanout=200)

    # Context manager and close
    cat = SegmentedCatalog(root)
    cat.close()
    with pytest.raises(RuntimeError, match="SegmentedCatalog is closed"):
        cat.snapshots()


def test_invalid_publish_parameters(tmp_path):
    cat_dir = tmp_path / "cat_invalid_pub"
    obs1 = make_synthetic_obs("130001")
    sum1 = make_synthetic_summary(obs1)

    with SegmentedCatalog(cat_dir) as cat:
        # Not lists
        with pytest.raises(ValueError, match="must be lists"):
            cat.publish("not_a_list", [sum1])
        with pytest.raises(ValueError, match="must be lists"):
            cat.publish([obs1], "not_a_list")

        # Empty lists
        with pytest.raises(ValueError, match="zero observations"):
            cat.publish([], [sum1])
        with pytest.raises(ValueError, match="zero layouts"):
            cat.publish([obs1], [])

        # Duplicate observation in batch
        with pytest.raises(ValueError, match="Duplicate observation"):
            cat.publish([obs1, obs1], [sum1])

        # Duplicate world in batch (different obs_id, same seed)
        obs1_dup = make_synthetic_obs("130001")
        obs1_dup["metrics"]["v"] = 1
        with pytest.raises(ValueError, match="Only one observation per world"):
            cat.publish([obs1, obs1_dup], [sum1])

        # Duplicate layout in batch
        with pytest.raises(ValueError, match="Duplicate layout"):
            cat.publish([obs1], [sum1, sum1])

        # Layout referencing observation not in batch
        obs2 = make_synthetic_obs("130002")
        sum2 = make_synthetic_summary(obs2)
        with pytest.raises(ValueError, match="references observation_id.*not in supplied"):
            cat.publish([obs1], [sum2])

        # World with zero layouts
        with pytest.raises(ValueError, match="zero layouts in publication batch"):
            cat.publish([obs1, obs2], [sum1])

        # Invalid parent snapshot_id
        with pytest.raises(ValueError, match="Invalid parent snapshot_id"):
            cat.publish([obs1], [sum1], parent="invalid_hex")

        # Unknown parent snapshot_id
        with pytest.raises(ValueError, match="Unknown parent snapshot"):
            cat.publish([obs1], [sum1], parent="0" * 64)


def test_deep_multi_world_tree_and_audit(tmp_path):
    cat_dir = tmp_path / "cat_deep_tree"
    worlds = []
    all_layouts = []

    # 8 worlds, each with 8 layouts = 64 layouts
    # leaf_entries=4 -> 2 leaves per world = 16 leaves total
    # fanout=3 -> Level 1: 6 nodes (3, 3, 3, 3, 3, 1) -> Level 2: 2 nodes (3, 3) -> Level 3 root: 1 node (2)
    anchors = geometry.anchors()[:8]
    for i in range(8):
        obs = make_synthetic_obs(f"14000{i}")
        worlds.append(obs)
        for a in anchors:
            all_layouts.append(make_synthetic_summary(obs, anchor=a, border_side=2048))

    with SegmentedCatalog(cat_dir, leaf_entries=4, fanout=3) as cat:
        snap_id = cat.publish(worlds, all_layouts)
        assert isinstance(snap_id, str)

        segments = list(cat.iter_segments(snap_id))
        assert len(segments) == 16
        for seg in segments:
            assert len(seg["layouts"]) == 4

        # Full audit passes
        audit_res = cat.audit(snap_id)
        assert audit_res["passed"] is True
        assert audit_res["worlds"] == 8
        assert audit_res["layouts"] == 64

        # Backup passes
        backup_dir = tmp_path / "cat_deep_backup"
        cat.backup(backup_dir)

    with SegmentedCatalog(backup_dir, leaf_entries=4, fanout=3) as restored:
        audit_res = restored.audit(snap_id)
        assert audit_res["passed"] is True
        assert audit_res["worlds"] == 8
        assert audit_res["layouts"] == 64


def test_schema_probe_rejection(tmp_path):
    root = tmp_path / "corrupt_schema_meta"
    root.mkdir()
    db_path = root / "pilot.sqlite"

    # Incompatible schema marker
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE schema_meta (revision TEXT PRIMARY KEY, status TEXT);")
    conn.execute("INSERT INTO schema_meta VALUES ('wrong-revision', 'active');")
    conn.close()

    with pytest.raises(ValueError, match="Incompatible catalog schema marker"):
        SegmentedCatalog(root)

    # Missing schema_meta marker
    db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE unrelated (x INT);")
    conn.close()

    with pytest.raises(ValueError, match="missing schema_meta marker"):
        SegmentedCatalog(root)

    # Personal database schema detected
    db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE personal_policy (x INT);")
    conn.close()

    with pytest.raises(ValueError, match="Personal database schema detected"):
        SegmentedCatalog(root)

