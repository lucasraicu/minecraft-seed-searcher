import copy
import json
import sqlite3

import pytest

from seed_search.realm.store import LIMIT, RealmStore, index_key


def result(index, seed=None):
    seed = str(index if seed is None else seed)
    return {"index": index, "seed": seed, "anchors": [
        {"id": f"{seed}:1:2", "seed": seed, "stronghold": [1, 2], "qualification": "PREDICTED"},
        {"id": f"{seed}:-3:4", "seed": seed, "stronghold": [-3, 4], "qualification": "PENDING"}], "counts": {"anchors": 2}}


def test_atomic_range_and_idempotent_retry(tmp_path):
    with RealmStore(tmp_path, {"config": {"search": {"workers": 1}}}) as store:
        store.configure_range(0, 4, 2)
        assert store.claim_range("a") == (0, 2)
        invalid = [result(0), result(1)]
        invalid[1]["anchors"][1]["id"] = "invalid"
        with pytest.raises(ValueError):
            store.complete_range(0, 2, invalid)
        assert store.status()["completed_seeds"] == 0
        assert list(store.iter_candidates()) == []
        assert list(store.iter_variant_tasks()) == []
        valid = [result(0), result(1)]
        assert store.complete_range(0, 2, valid)
        assert not store.complete_range(0, 2, list(reversed(valid)))
        assert store.status()["completed_seeds"] == 2
        assert store.status()["counts"] == {"anchors": 4}
        assert len(list(store.iter_candidates(batch_size=1))) == 4
        assert len(list(store.iter_candidates("PENDING", 1))) == 2
        stored = store.db.execute("SELECT result FROM seeds ORDER BY idx LIMIT 1").fetchone()[0]
        summary = json.loads(stored)
        assert "anchors" not in summary and "anchor_ids" in summary
        assert list(store.iter_results(1)) == valid
        assert len(list(store.iter_variant_tasks(variant="v1", batch_size=1))) == 4
        assert len(list(store.iter_variant_tasks(variant="v2", batch_size=1))) == 4
        plan = ' '.join(str(row) for row in store.db.execute('EXPLAIN QUERY PLAN SELECT variant,status,count(*) FROM variant_tasks GROUP BY variant,status'))
        assert 'USING COVERING INDEX variant_task_status' in plan
        assert 'TEMP B-TREE' not in plan
        valid[0]["counts"]["anchors"] = 7
        with pytest.raises(ValueError, match="differs"):
            store.complete_range(0, 2, valid)


def test_resume_retries_only_uncommitted_ranges_and_normalized_hash(tmp_path):
    identity = {"config": {"search": {"workers": 1, "max_workers": 36, "batch_size": 2, "run_key": "fixed"}}, "config_sha256": "oldhash", "code": "fixed"}
    with RealmStore(tmp_path, identity) as store:
        store.configure_range(0, 6, 2)
        a = store.claim_range("a")
        b = store.claim_range("b")
        store.complete_range(*a, [result(0), result(1)])
    changed = copy.deepcopy(identity)
    changed["config"]["search"].update(workers=3, max_workers=12, batch_size=1)
    changed["config_sha256"] = "newhash"
    with RealmStore(tmp_path, changed, resume=True) as store:
        store.configure_range(0, 6, 1)
        assert store.recover_assignments() == 1
        assert store.claim_range("c") == b
        assert store.claim_range("d") == (4, 5)
    changed["config"]["search"]["run_key"] = "different"
    with pytest.raises(ValueError, match="Incompatible"):
        RealmStore(tmp_path, changed, resume=True)


def test_full64_boundary_and_split_retry(tmp_path):
    with RealmStore(tmp_path) as store:
        store.configure_range(LIMIT - 3, LIMIT, 3)
        assert store.claim_range(1) == (LIMIT - 3, LIMIT)
        store.recover_assignments()
        assert store.claim_range(2, max_seeds=1) == (LIMIT - 3, LIMIT - 2)
        assert store.claim_range(3) == (LIMIT - 2, LIMIT)
        store.complete_range(LIMIT - 3, LIMIT - 2, [result(LIMIT - 3, -3)])
        store.complete_range(LIMIT - 2, LIMIT, [result(LIMIT - 2, -2), result(LIMIT - 1, -1)])
        assert store.claim_range(4) is None
        assert store.status()["remaining_seeds"] == 0
        assert [r["index"] for r in store.iter_results(1)] == list(range(LIMIT - 3, LIMIT))
        assert store.db.execute("SELECT typeof(start),end FROM ranges ORDER BY start DESC LIMIT 1").fetchone() == ("text", index_key(LIMIT))


def test_rollback_on_database_failure_and_record_accessors(tmp_path):
    with RealmStore(tmp_path) as store:
        store.configure_range(0, 2, 2)
        store.claim_range(1)
        store.db.execute("CREATE TRIGGER fail_seed BEFORE INSERT ON seeds WHEN NEW.idx='00000000000000000001' BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
        with pytest.raises(sqlite3.IntegrityError):
            store.complete_range(0, 2, [result(0), result(1)])
        assert store.status()["completed_seeds"] == 0
        assert list(store.iter_results()) == []
        assert list(store.iter_candidates()) == []
        store.db.execute("DROP TRIGGER fail_seed")
        store.complete_range(0, 2, [result(0), result(1)])
        cid = "0:1:2"
        store.upsert_variant(cid, "v1", [0, 0], {"status": "pending"})
        store.upsert_variant(cid, "v1", [0, 0], {"status": "complete"})
        assert store.get_variant(cid, "v1", [0, 0])["result"] == {"status": "complete"}
        assert len(list(store.iter_variants(batch_size=1))) == 1
        assert list(store.iter_variant_tasks(variant="v1", status="started")) == [{"candidate_id": cid, "variant": "v1", "status": "started"}]
        store.set_variant_task_status(cid, "v1", "complete")
        assert len(list(store.iter_variant_tasks(status="complete"))) == 1
        oid = store.upsert_observation(cid, {"id": "test", "value": 1})
        store.upsert_observation(cid, {"id": "test", "value": 2})
        assert store.get_observation(oid)["value"] == 2
        assert len(list(store.iter_observations(batch_size=1))) == 1
        assert store.get_observation("missing") is None


def test_candidate_updates_keep_identity_and_require_eligibility_opt_in(tmp_path):
    with RealmStore(tmp_path) as store:
        store.configure_range(0, 1)
        store.claim_range(1)
        original = result(0)
        store.complete_range(0, 1, [original])
        cid = "0:1:2"
        store.upsert_candidate({"id": cid, "score": {"total": 4}})
        assert store.get_candidate(cid)["score"] == {"total": 4}
        assert store.get_candidate(cid)["stronghold"] == [1, 2]
        assert list(store.iter_results())[0]["anchors"][0]["score"] == {"total": 4}
        with pytest.raises(ValueError, match="immutable"):
            store.upsert_candidate({"id": cid, "seed": "1"})
        with pytest.raises(ValueError, match="authorization"):
            store.upsert_candidate({"id": cid, "qualification": "VERIFIED"})
        store.upsert_candidate({"id": cid, "qualification": "VERIFIED"}, allow_qualification_change=True)
        assert store.status()["candidate_counts"]["VERIFIED"] == 1
        # Digest still covers original worker results, not later rescores/evidence.
        assert not store.complete_range(0, 1, [original])
