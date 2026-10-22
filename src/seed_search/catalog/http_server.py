"""Private loopback Catalog-only preview; never initializes SweepManager."""
import argparse
import signal
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
from .service import CatalogService,ServiceError
from ..web import catalog_routes


def make_handler(catalog):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup();self.connection.settimeout(10)
        def _allowed(self):
            allowed={f'http://{host}:{port}' for host in ('localhost','127.0.0.1') for port in (5173,self.server.server_port)}
            origin=self.headers.get('Origin');referer=self.headers.get('Referer')
            host=self.headers.get('Host')
            return (host in {f'localhost:{self.server.server_port}',f'127.0.0.1:{self.server.server_port}'} and
                self.headers.get('Sec-Fetch-Site','').lower()!='cross-site' and
                (not origin or origin in allowed) and
                (not referer or f'{urlparse(referer).scheme}://{urlparse(referer).netloc}' in allowed))
        def end_headers(self):
            origin=self.headers.get('Origin')
            if origin and self._allowed():
                self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Vary','Origin')
                self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS');self.send_header('Access-Control-Allow-Headers','Content-Type')
            super().end_headers()
        def do_OPTIONS(self):
            catalog_routes.respond(self,200 if self._allowed() else 403,dict(ok=self._allowed()))
        def do_GET(self):
            if not self._allowed():catalog_routes.respond(self,403,dict(ok=False,error='Origin or Host not allowed',code='forbidden'));return
            if not catalog_routes.get(self,catalog):catalog_routes.respond(self,404,dict(ok=False,error='Not found',code='not_found'))
        def do_POST(self):
            if not self._allowed():catalog_routes.respond(self,403,dict(ok=False,error='Origin or Host not allowed',code='forbidden'));return
            try:body=catalog_routes.read_body(self)
            except (ServiceError,ValueError,UnicodeError):
                catalog_routes.respond(self,400,dict(ok=False,error='Invalid JSON request',code='invalid_request'));return
            if not catalog_routes.post(self,body,catalog):catalog_routes.respond(self,404,dict(ok=False,error='Not found',code='not_found'))
        def log_message(self,*_):pass
    return Handler


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',required=True);parser.add_argument('--port',type=int,default=3001)
    parser.add_argument('--query-processes',type=int,choices=(0,1,2),default=2)
    args=parser.parse_args(argv)
    catalog=CatalogService(args.root,query_processes=args.query_processes)
    previous=None
    def stop(*_):raise KeyboardInterrupt
    try:
        # Validate bounded immutable metadata before accepting HTTP. Reuse still
        # rehashes all manifest pages; failed initialization closes owned workers.
        from .automation_query import available
        if available(args.root):catalog.snapshots()
        if threading.current_thread() is threading.main_thread():
            previous=signal.signal(signal.SIGTERM,stop)
        with ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(catalog)) as server:
            server.daemon_threads=True
            print(f'Private Catalog backend http://127.0.0.1:{server.server_port}',flush=True)
            try:server.serve_forever()
            except KeyboardInterrupt:pass
    finally:
        catalog.close()
        if previous is not None:signal.signal(signal.SIGTERM,previous)


if __name__=='__main__':main()
