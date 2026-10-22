"""Coordinator checks for hazards beyond worker happy-path persistence tests."""
import gzip
import hashlib
import json
import os
import sqlite3
import stat
import pytest
from seed_search.catalog.artifacts import ArtifactStore
from seed_search.catalog.store import CatalogStore
from seed_search.catalog.models import identity, empty_observation, observation_id, world_id, SUMMARY_REVISION
from seed_search.catalog.codec import layout_id, MISSING


def records():
    obs=empty_observation(identity(0,model_id='MC_26_50',native_sha256='a'*64,source_sha256='b'*64))
    oid=observation_id(obs)
    row={'revision':SUMMARY_REVISION,'observation_id':oid,'world_id':world_id(obs['identity']),
        'layout_id':layout_id(oid,[0,0],2048),'seed':'0','anchor':[0,0],'border_side':2048,
        'counts':[[0]*4 for _ in range(14)],'structure_nearest_d2':[MISSING]*14,
        'biome_nearest_d2':[MISSING]*9,'biome_witness_refs':[MISSING]*9,
        'complete':[[False]*4 for _ in range(23)]}
    return obs,row


def test_temporary_directory_symlink_rejected(tmp_path):
    outside=tmp_path/'outside'; outside.mkdir(); (outside/'keep').write_text('keep')
    root=tmp_path/'artifacts'; root.mkdir(); (root/'.tmp').symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError): ArtifactStore(root)
    assert (outside/'keep').read_text()=='keep'


def test_opening_reader_does_not_delete_active_staging(tmp_path):
    root=tmp_path/'artifacts'; ArtifactStore(root)
    live=root/'.tmp'/'live-staging'; live.write_text('writer is alive')
    ArtifactStore(root)
    assert live.read_text()=='writer is alive'


def test_directory_fsync_failure_is_not_silenced(tmp_path,monkeypatch):
    store=ArtifactStore(tmp_path/'artifacts'); real=os.fsync
    def fail(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError('directory durability unavailable')
        return real(fd)
    monkeypatch.setattr(os,'fsync',fail)
    with pytest.raises(OSError): store.put_json({'x':1})


def test_gzip_missing_trailer_is_not_valid_artifact(tmp_path):
    store=ArtifactStore(tmp_path/'artifacts')
    raw=b'{"x":1}'; data=gzip.compress(raw,mtime=0)[:-8]; sha=hashlib.sha256(data).hexdigest()
    key=f'{sha[:2]}/{sha}.json.gz'; target=store.root/key
    target.parent.mkdir(); target.write_bytes(data)
    manifest={'sha256':sha,'relative_key':key,'byte_length':len(data),'uncompressed_length':len(raw),'codec':'gzip'}
    with pytest.raises(ValueError): store.get_json(manifest)


def test_database_symlink_and_incompatible_db_are_not_modified(tmp_path):
    foreign=tmp_path/'foreign.sqlite'
    with sqlite3.connect(foreign) as db: db.execute('CREATE TABLE private_data (id INTEGER)')
    before=foreign.read_bytes()
    root=tmp_path/'catalog';root.mkdir();(root/'catalog.sqlite').symlink_to(foreign)
    with pytest.raises(ValueError): CatalogStore(root)
    assert foreign.read_bytes()==before
    (root/'catalog.sqlite').unlink();(root/'catalog.sqlite').write_bytes(before)
    with pytest.raises(ValueError): CatalogStore(root)
    assert (root/'catalog.sqlite').read_bytes()==before


def test_snapshot_manifest_binds_actual_payload_hash(tmp_path):
    obs,row=records()
    with CatalogStore(tmp_path/'catalog') as store:
        sid=store.publish_snapshot([obs],[row])
        blob=bytearray(store.conn.execute('SELECT payload_blob FROM layout').fetchone()[0])
        # Change a valid completion bit, and update its local checksum as well.
        blob[352]=1; data=bytes(blob)
        store.conn.execute('UPDATE layout SET payload_blob=?, blob_sha256=?',(data,hashlib.sha256(data).hexdigest()))
        with pytest.raises(ValueError): store.snapshot(sid)


def test_replay_verifies_existing_published_manifest(tmp_path):
    obs,row=records()
    with CatalogStore(tmp_path/'catalog') as store:
        sid=store.publish_snapshot([obs],[row])
        key=store.conn.execute('SELECT relative_key FROM artifact JOIN catalog_snapshot ON artifact.sha256=catalog_snapshot.manifest_sha256 WHERE snapshot_id=?',(sid,)).fetchone()[0]
        (store.artifacts.root/key).write_bytes(b'corrupt')
        with pytest.raises(ValueError): store.publish_snapshot([obs],[row])
