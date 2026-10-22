"""Coordinator adversarial checks beyond worker-returned storage tests."""
import json
import pytest
from seed_search.catalog.segments import SegmentedCatalog
from tests.catalog.test_segments import make_synthetic_obs,make_synthetic_summary


def test_identical_append_is_noop_but_payload_change_requires_explicit_replacement(tmp_path):
    obs=make_synthetic_obs(7);row=make_synthetic_summary(obs)
    with SegmentedCatalog(tmp_path/'pilot') as store:
        sid=store.publish([obs],[row]);assert store.publish([obs],[row],parent=sid)==sid
        assert len(store.snapshots())==1
        changed=dict(row,counts=[[1]*4]+row['counts'][1:])
        with pytest.raises(ValueError,match='Conflict'):store.publish([obs],[changed],parent=sid)


@pytest.mark.parametrize('corruption',['drop_membership','header','layout_count','observation_binding'])
def test_serving_rejects_sql_corruption_without_loading_raw_biomes(tmp_path,corruption):
    obs=make_synthetic_obs(7);row=make_synthetic_summary(obs)
    with SegmentedCatalog(tmp_path/'pilot') as store:
        sid=store.publish([obs],[row])
        if corruption=='drop_membership':store.conn.execute('DELETE FROM snapshot_membership WHERE snapshot_id=?',(sid,))
        elif corruption=='header':
            header=dict(obs['identity']);header.pop('seed');header['native_sha256']='d'*64
            store.conn.execute('UPDATE snapshot_root SET header_json=? WHERE snapshot_id=?',(json.dumps(header),sid))
        elif corruption=='layout_count':store.conn.execute('UPDATE snapshot_root SET layout_count=0 WHERE snapshot_id=?',(sid,))
        else:store.conn.execute('UPDATE observation_ref SET observation_id=? WHERE snapshot_id=?',('0'*64,sid))
        with pytest.raises(ValueError):list(store.iter_segments(sid))


def test_corrupt_root_descriptor_cannot_be_rehashed_to_rebind_same_snapshot(tmp_path):
    obs=make_synthetic_obs(7);row=make_synthetic_summary(obs)
    with SegmentedCatalog(tmp_path/'pilot') as store:
        sid=store.publish([obs],[row]);record=store.conn.execute('SELECT manifest_sha256 FROM snapshot_root WHERE snapshot_id=?',(sid,)).fetchone()
        values=store.conn.execute('SELECT sha256,relative_key,byte_length,uncompressed_length,codec FROM artifact_ref WHERE sha256=?',record).fetchone()
        descriptor=store.artifacts.get_json(dict(zip(('sha256','relative_key','byte_length','uncompressed_length','codec'),values)))
        descriptor['parent_snapshot_id']='f'*64
        manifest=store.artifacts.put_json(descriptor)
        store.conn.execute('INSERT INTO artifact_ref VALUES(?,?,?,?,?,?)',(*[manifest[k] for k in ('sha256','relative_key','byte_length','uncompressed_length','codec')],'2026-10-20'))
        store.conn.execute('UPDATE snapshot_root SET manifest_sha256=? WHERE snapshot_id=?',(manifest['sha256'],sid))
        with pytest.raises(ValueError,match='identity'):list(store.iter_segments(sid))
