"""Serving boundaries independent of ongoing storage implementation."""
import copy
import random
from decimal import Decimal
import pytest
from seed_search.catalog.service import CatalogService,ServiceError,TopWorlds


def candidate(wid,key):return dict(world_id=str(wid),_sort_key=key)


def test_streaming_topk_keeps_global_world_winners_after_eviction():
    rng=random.Random(294);rows=[candidate(w, (Decimal(rng.randrange(1000))/7,w,a)) for w in range(500) for a in range(5)]
    rng.shuffle(rows);expected={}
    for row in rows:
        if row['world_id'] not in expected or row['_sort_key']<expected[row['world_id']]['_sort_key']:expected[row['world_id']]=row
    for order in (rows,list(reversed(rows))):
        top=TopWorlds(50)
        for row in order:top.offer(row)
        assert top.results()==sorted(expected.values(),key=lambda r:r['_sort_key'])[:50]
        assert len(top.members)<=50 and len(top.heap)<=100


def test_cursor_integrity_expiry_and_full_precision():
    service=CatalogService(secret=b'fixed-test-secret')
    payload=dict(snapshot='f'*64,request='c'*64,size=50,expires=1e20,
        last=['-5100100100.123456789012345678901234567890','4',str((1<<64)-1),'-976','976','b'*64])
    token=service._token(payload);assert service._decode(token)==payload
    with pytest.raises(ServiceError):service._decode(token[:-2]+'ee')
    with pytest.raises(ServiceError,match='expired'):service._decode(service._token(dict(payload,expires=0)))
    with pytest.raises(ServiceError):service._decode('x'*9000)


def test_unconfigured_status_and_capabilities_are_honest():
    service=CatalogService();assert service.status()['available'] is False
    cap=service.capabilities();assert len(cap['registry']['categories'])==8
    assert len(cap['registry']['features'])==23
    assert cap['anchor_modes']==['recommended','origin']
    assert cap['border_sides']==[2048,4096,8192] and len(cap['presets'])==8
    with pytest.raises(ServiceError):service.query({})
    with pytest.raises(ServiceError):service.query({'request':{},'page_size':True})


def test_busy_queue_is_bounded_and_releases_after_errors():
    service=CatalogService()
    for _ in range(4):service.admission.acquire()
    with pytest.raises(ServiceError,match='busy'):
        with service._slot():pass
    for _ in range(4):service.admission.release()
    with pytest.raises(RuntimeError):
        with service._slot():raise RuntimeError('injected')
    assert service.admission.acquire(blocking=False);service.admission.release()
    assert service.execution.acquire(blocking=False);service.execution.release()
