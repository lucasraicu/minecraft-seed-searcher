import json
import pytest
from test_automation_query import catalog
from seed_search.catalog.store import AutomationStore
from seed_search.catalog.registry import digest
from seed_search.catalog.ingestion import atomic_json


def test_cached_query_index_rehashes_every_bound_page(catalog,monkeypatch):
    service,sid=catalog;store=AutomationStore(service.root);manifest=store.snapshot(sid)
    manifest['generation']+=1;sid=digest(manifest)
    store._PAGE_THRESHOLD_BYTES=1;store._PAGE_ITEM_LIMIT=1
    artifact=store._write_manifest(manifest,compression_level=1)
    binding=dict(revision='catalog-snapshot-binding-v2',snapshot_id=sid,generation=manifest['generation'],artifact=artifact)
    atomic_json(store.snapshots_dir/(sid+'.json'),binding)
    first=service._query_snapshot(store,sid)
    assert 'memberships' not in first and first['worlds']==manifest['worlds']
    assert service.cache_size<=service.cache_bytes
    monkeypatch.setattr(store,'snapshot',lambda *_:pytest.fail('A cache hit parsed the full manifest'))
    assert service._query_snapshot(store,sid)==first
    cached=service.cache[('verified-query-snapshot',sid)][0]
    assert len(cached['artifacts'])>1
    page=cached['artifacts'][-1];path=store.artifacts.root/page['relative_key'];wire=path.read_bytes()
    corrupted=bytearray(wire);corrupted[len(corrupted)//2]^=1;path.write_bytes(corrupted)
    with pytest.raises(ValueError,match='sha256 mismatch'):service._query_snapshot(store,sid)


def test_cached_query_index_rejects_rebound_snapshot(catalog):
    service,sid=catalog;store=AutomationStore(service.root);service._query_snapshot(store,sid)
    binding=store._binding(sid);binding['generation']+=1
    atomic_json(store.snapshots_dir/(sid+'.json'),binding)
    with pytest.raises(ValueError,match='binding changed'):service._query_snapshot(store,sid)


def test_query_index_obeys_existing_shared_cache_budget(catalog,monkeypatch):
    service,sid=catalog;store=AutomationStore(service.root);service.cache_bytes=1
    original=store.snapshot;calls=[]
    def snapshot(sid):calls.append(sid);return original(sid)
    monkeypatch.setattr(store,'snapshot',snapshot)
    a=service._query_snapshot(store,sid);b=service._query_snapshot(store,sid)
    assert a==b and len(calls)==2 and service.cache_size==0 and not service.cache


def test_query_context_cannot_mutate_future_queries(catalog):
    service,sid=catalog;store=AutomationStore(service.root)
    first=service._query_snapshot(store,sid);world=first['worlds'][0]['world_id']
    first['worlds'][0]['world_id']='f'*64
    second=service._query_snapshot(store,sid)
    assert second['worlds'][0]['world_id']==world


def test_http_metadata_initialization_failure_closes_owned_workers(monkeypatch,tmp_path):
    from seed_search.catalog import http_server,automation_query
    closed=[]
    class Broken:
        def snapshots(self):raise ValueError('Corrupt saved metadata')
        def close(self):closed.append(True)
    monkeypatch.setattr(http_server,'CatalogService',lambda *a,**k:Broken())
    monkeypatch.setattr(automation_query,'available',lambda *a:True)
    with pytest.raises(ValueError,match='Corrupt saved metadata'):
        http_server.main(['--root',str(tmp_path)])
    assert closed==[True]
