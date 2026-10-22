"""Bounded Catalog HTTP adapter, shared by integrated and standalone loopback servers."""
import json
import os
from urllib.parse import urlparse,parse_qs
from ..catalog.service import CatalogService,ServiceError
from ..catalog.request import UnsupportedFeatureError

_service=None


def service():
    global _service
    if _service is None:_service=CatalogService(os.environ.get('SEED_SEARCH_CATALOG_ROOT'))
    return _service


def respond(handler,status,value):
    encoded=json.dumps(value,allow_nan=False,separators=(',',':')).encode()
    handler.send_response(status);handler.send_header('Content-Type','application/json; charset=utf-8')
    handler.send_header('Content-Length',str(len(encoded)));handler.send_header('Cache-Control','no-store')
    handler.send_header('X-Content-Type-Options','nosniff');handler.end_headers();handler.wfile.write(encoded)


def _call(handler,operation):
    try:
        result=operation()
        respond(handler,409 if result.get('code')=='product_gated' else 200,result)
    except UnsupportedFeatureError as exc:respond(handler,409,dict(ok=False,error=str(exc),code='capability_error'))
    except ServiceError as exc:respond(handler,exc.status,dict(ok=False,error=str(exc),code=exc.code))
    except (ValueError,TypeError,KeyError):respond(handler,400,dict(ok=False,error='Invalid request or unavailable snapshot',code='invalid_request'))
    except Exception:respond(handler,503,dict(ok=False,error='Catalog data is unavailable; inspect the local audit',code='catalog_unavailable'))


def get(handler,catalog=None):
    url=urlparse(handler.path);path=url.path
    if not path.startswith('/api/catalog/'):return False
    catalog=catalog or service()
    def operation():
        if path=='/api/catalog/status':return catalog.status()
        if path=='/api/catalog/automation-status':
            from ..catalog.automation import status
            return dict(ok=True,catalog_root=str(catalog.root) if catalog.root else None,
                        **(status(catalog.root) if catalog.root else dict(configured=False,state='unconfigured')))
        if path=='/api/catalog/capabilities':
            params=parse_qs(url.query,keep_blank_values=True)
            if set(params)-{'snapshot_id'} or any(len(v)!=1 for v in params.values()):raise ServiceError('Expected one optional snapshot_id')
            return catalog.capabilities(params['snapshot_id'][0] if 'snapshot_id' in params else None)
        if path=='/api/catalog/products':
            params=parse_qs(url.query,keep_blank_values=True)
            if set(params)-{'snapshot_id'} or ('snapshot_id' in params and len(params['snapshot_id'])!=1):
                raise ServiceError('Expected one optional snapshot_id')
            return catalog.products(params['snapshot_id'][0] if 'snapshot_id' in params else None)
        if path=='/api/catalog/snapshots':return catalog.snapshots()
        if path=='/api/catalog/detail':
            params=parse_qs(url.query,keep_blank_values=True)
            if set(params)!={'snapshot_id','world_id','layout_id'} or any(len(v)!=1 for v in params.values()):
                raise ServiceError('Expected one snapshot_id, world_id and layout_id')
            return catalog.detail(params['snapshot_id'][0],params['world_id'][0],params['layout_id'][0])
        raise ServiceError('Unknown Catalog endpoint','not_found',404)
    _call(handler,operation);return True


def post(handler,payload,catalog=None):
    path=urlparse(handler.path).path
    if path=='/api/catalog/automation-control':
        def operation():
            if not isinstance(payload,dict) or set(payload)!={'revision','action'} or payload['revision']!='catalog-automation-control-v2':
                raise ServiceError('Expected versioned public worker action')
            current=catalog or service()
            if current.root is None:raise ServiceError('Catalog root is not configured','unavailable',503)
            from ..catalog.automation import control
            return dict(ok=True,**control(current.root,payload['action']))
        _call(handler,operation);return True
    if path not in ('/api/catalog/query','/api/catalog/product-results','/api/catalog/biome-scope'):return False
    _call(handler,lambda:((catalog or service()).biome_scope(payload) if path.endswith('/biome-scope') else (catalog or service()).query(payload) if path.endswith('/query')
                         else (catalog or service()).product_results(payload)));return True


def read_body(handler):
    from ..catalog.request import _unique
    raw=handler.headers.get('Content-Length','')
    if not raw.isdigit() or not 2<=int(raw)<=16384:raise ServiceError('JSON body must be 2–16384 bytes')
    if handler.headers.get('Transfer-Encoding'):raise ServiceError('Transfer encoding unsupported')
    if handler.headers.get_content_type()!='application/json':raise ServiceError('Expected application/json')
    data=handler.rfile.read(int(raw))
    if len(data)!=int(raw):raise ServiceError('Incomplete request body')
    return json.loads(data,object_pairs_hook=_unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
