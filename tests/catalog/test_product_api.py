"""Product serving must not execute extraction or weaken query-v1."""
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from seed_search.catalog.http_server import make_handler
from seed_search.catalog.service import CatalogService, ServiceError
from tests.catalog.test_http_catalog import request


def body(product_id='research.origin.village.r2000'):
    return dict(revision='catalog-product-request-v1', snapshot_id='a'*64, product_id=product_id)


def test_registry_available_without_catalog_and_promises_gated():
    registry = CatalogService().products()
    assert {p['id'] for p in registry['pillars']} == {'realm','presets','personalized','rare'}
    presets = [p for p in registry['products'] if p['kind'] == 'preset']
    records = [p for p in registry['products'] if p['kind'] == 'record']
    assert len(presets) == 16 and len(records) == 22
    for product in presets + records:
        result = CatalogService().product_results(body(product['id']))
        assert not result['ok'] and result['code'] == 'product_gated'
        assert result['missing_dependencies'] and not result['results']


@pytest.mark.parametrize('value', [{}, [], dict(body(), path='/tmp'),
                                  dict(body(), snapshot_id='../x'), dict(body(), product_id=123),
                                  dict(body(), revision='future')])
def test_product_request_strict(value):
    with pytest.raises(ServiceError):CatalogService().product_results(value)


def test_http_gates_and_cross_origin_are_enforced():
    service = CatalogService()
    with ThreadingHTTPServer(('127.0.0.1',0), make_handler(service)) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            code, data = request(server, 'GET', '/api/catalog/products')
            assert code == 200 and data['revision'] == 'catalog-products-v1'
            status_code, worker = request(server, 'GET', '/api/catalog/automation-status')
            assert status_code == 200 and worker['catalog_root'] is None and worker['configured'] is False
            preset = next(p for p in data['products'] if p['kind'] == 'preset')
            code, data = request(server, 'POST', '/api/catalog/product-results',
                                 json.dumps(body(preset['id'])), {'Content-Type':'application/json'})
            assert code == 409 and data['code'] == 'product_gated'
            assert request(server, 'POST', '/api/catalog/product-results', '{}',
                           {'Content-Type':'application/json','Origin':'http://evil.example'})[0] == 403
            assert request(server, 'POST', '/api/catalog/product-results',
                           '{"snapshot_id":"a","snapshot_id":"b"}',
                           {'Content-Type':'application/json'})[0] == 400
        finally:
            server.shutdown()
            thread.join(timeout=5)


def test_precomputed_results_pin_snapshot_and_never_reextract(tmp_path,monkeypatch):
    from seed_search.catalog.product_views import derive_previews,write_previews
    from seed_search.catalog.segments import SegmentedCatalog
    from tests.catalog.test_integrated_pilot import sample
    from seed_search.catalog import extract
    root=tmp_path/'public';obs,layouts=sample(-(1<<63))
    with SegmentedCatalog(root) as store:
        sid=store.publish([obs],layouts)
        payload=derive_previews(store,sid)
    service=CatalogService(root)
    request_body=dict(body(),snapshot_id=sid)
    with pytest.raises(ServiceError) as error:service.product_results(request_body)
    assert error.value.code=='preview_unavailable'
    path=write_previews(root,payload)
    monkeypatch.setattr(extract,'extract_observation',lambda *a,**k:pytest.fail('Serving must not extract'))
    result=service.product_results(request_body)
    assert result['results'][0]['seed']==str(-(1<<63))
    assert result['scope']['radius']==2000 and result['population_worlds']==1
    # An unrelated later snapshot does not silently replace the requested artifact.
    new,rows=sample(77)
    with SegmentedCatalog(root) as store:new_sid=store.publish([new],rows,parent=sid)
    assert service.product_results(request_body)['snapshot_id']==sid
    with pytest.raises(ServiceError):service.product_results(dict(request_body,snapshot_id=new_sid))
    path.write_text('{}')
    with pytest.raises(ServiceError) as error:service.product_results(request_body)
    assert error.value.code=='integrity_error'
