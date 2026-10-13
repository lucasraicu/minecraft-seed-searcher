"""Canonical byte parity, owned buffers and durable retry for locked templates."""
import json
import pytest

from test_outpost_blueprint import native
from seed_search.realm.config import locked_blueprint_config,river_blueprint_config,outpost_blueprint_config
from seed_search.realm.native_batch import Prototype,semantic_record
from seed_search.realm.native_encoding import fast_records,candidate_encoding,summary_encoding,LockedPendingEncoder
from seed_search.realm.store import RealmStore,canonical
from seed_search.seeds import seed_from_index


@pytest.mark.parametrize('factory',[locked_blueprint_config,river_blueprint_config,outpost_blueprint_config])
@pytest.mark.parametrize('synthetic',[False,True])
def test_locked_templates_match_all_bytes_and_durable_records(native,tmp_path,factory,synthetic):
    p=Prototype(native.directory,factory())
    fixtures=[(x,-7,k) for x in (-2000,-1,0,1999) for k in range(-1,28)] if synthetic else None
    seeds=[seed_from_index(i,120280003000) for i in range(len(fixtures) if synthetic else 512)]
    with RealmStore(tmp_path,{'config':p.cfg}) as store:
        store.configure_range(0,len(seeds),len(seeds));store.claim_range('test')
        with p.sweep(seeds,1,fixtures=fixtures) as batch:
            reference=batch.records();fast=fast_records(batch,0,store)
            owned=[]
            for e,d in zip(fast,reference):
                assert [candidate_encoding(a,canonical) for a in e['anchors']]==[canonical(a) for a in d['anchors']]
                summary=summary_encoding(e)
                if summary is None:row=e
                else:
                    row=json.loads(summary);row.pop('anchor_ids')
                    row['anchors']=[json.loads(candidate_encoding(a,canonical)) for a in e['anchors']]
                assert semantic_record(row)==semantic_record(d)
                assert row['prototype']==d['prototype']
                assert row['stage_seconds']==d['stage_seconds']
                owned.append(row)
            prepared=store.prepare_range(0,len(seeds),fast)
            # Same canonical bytes and digest through the public dictionary path.
            oracle=store.prepare_range(0,len(seeds),owned)
            assert prepared.digest==oracle.digest
            assert prepared.candidate_rows==oracle.candidate_rows
            batch.close()
        assert store.complete_prepared(prepared,lease=('test',1))
        assert not store.complete_prepared(oracle)
        assert list(map(semantic_record,store.iter_results()))==list(map(semantic_record,reference))
        for table,rows in [('discovery_tasks',len(seeds)*2),('variant_tasks',sum(len(r['anchors']) for r in reference))]:
            assert store.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==rows
        assert store.db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'


def test_locked_template_bound_fallback_and_input_validation(native,tmp_path,monkeypatch):
    p=Prototype(native.directory,outpost_blueprint_config())
    monkeypatch.setattr(LockedPendingEncoder,'limit',0)
    with RealmStore(tmp_path,{'config':p.cfg}) as store:
        with p.sweep([-1,0,2**63-1],1,fixtures=[(0,0,10)]*3) as batch:
            actual=fast_records(batch,2**64-3,store)
            assert list(map(semantic_record,actual))==list(map(semantic_record,batch.records(2**64-3)))
            assert not p._locked_pending_encoder.templates
            for index in (True,-1,2**64-2):
                with pytest.raises(ValueError):fast_records(batch,index,store)
            batch.close()
            with pytest.raises(ValueError,match='Closed'):fast_records(batch,0,store)


def test_shared_canonical_encoder_matches_original_bytes_concurrently():
    from concurrent.futures import ThreadPoolExecutor
    values=[{'unicode':'雪\\\"\n\ud800','integers':[0,-2**63,2**64-1],
             'floats':[-0.,.125,-.875,1e-30,1e100],'null':None,'bool':True},
            [],{},('nested',{'z':2,'a':[3,4]})]*100
    expected=[json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False) for v in values]
    with ThreadPoolExecutor(max_workers=4) as pool:assert list(pool.map(canonical,values))==expected
    for v in (float('nan'),float('inf'),float('-inf')):
        with pytest.raises(ValueError):canonical(v)
    cycle=[];cycle.append(cycle)
    with pytest.raises(ValueError):canonical(cycle)
