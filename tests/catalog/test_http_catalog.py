import http.client
import json
import threading
from http.server import ThreadingHTTPServer
import pytest
from seed_search.catalog.http_server import make_handler
from seed_search.catalog.service import CatalogService


@pytest.fixture
def server():
    with ThreadingHTTPServer(('127.0.0.1',0),make_handler(CatalogService())) as srv:
        thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
        try:yield srv
        finally:srv.shutdown();thread.join(timeout=5)


def request(server,method,path,body=None,headers=None):
    conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
    try:
        conn.request(method,path,body=body,headers=headers or {});r=conn.getresponse()
        return r.status,json.loads(r.read())
    finally:conn.close()


def test_status_capabilities_and_unknown_endpoints(server):
    status,data=request(server,'GET','/api/catalog/status');assert status==200 and not data['available']
    status,data=request(server,'GET','/api/catalog/capabilities');assert status==200 and len(data['registry']['features'])==23
    status,data=request(server,'GET','/api/sweep/start');assert status==404
    status,data=request(server,'GET','/api/catalog/detail?snapshot_id=x');assert status==400


@pytest.mark.parametrize('headers',[{'Origin':'http://evil.example'},{'Referer':'http://evil.example/path'},
    {'Sec-Fetch-Site':'cross-site'},{'Host':'evil.example'}])
def test_cross_origin_and_rebinding_rejected(server,headers):
    assert request(server,'POST','/api/catalog/query','{}',headers)[0]==403
    assert request(server,'GET','/api/catalog/status',headers=headers)[0]==403


@pytest.mark.parametrize('body',['{"request":{},"request":{}}','{"request":NaN}','[]','{"request":'])
def test_json_invalid_bodies_cannot_query(server,body):
    assert request(server,'POST','/api/catalog/query',body,{'Content-Type':'application/json'})[0]==400


def test_large_body_and_content_type_rejected(server):
    assert request(server,'POST','/api/catalog/query',' '*17000,{'Content-Type':'application/json'})[0]==400
    assert request(server,'POST','/api/catalog/query','{}',{'Content-Type':'text/plain'})[0]==400
