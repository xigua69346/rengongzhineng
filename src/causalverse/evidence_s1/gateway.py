"""Loopback-only independent HTTP service; no paid API, control, upload or proxy routes."""
import argparse
import json
import secrets
import socket
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .service import EvidenceService
from .protection_v11 import check

ASSETS = Path(__file__).parent / 'console'

def make_server(service, port=8769):
    sessions = {}
    guard = threading.BoundedSemaphore(1)
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args):
            pass  # Avoid private identifiers/cookies in access logs.

        def reply(self, code, value, mime='application/json', cookie=None):
            body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode() if mime == 'application/json' else value
            self.send_response(code)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            if cookie:
                self.send_header('Set-Cookie', cookie)
            self.end_headers()
            self.wfile.write(body)

        def admit(self):
            port = self.server.server_port
            hosts = (f'127.0.0.1:{port}', f'localhost:{port}')
            if self.headers.get('Host') not in hosts:
                raise PermissionError('HOST_DENIED')
            origin = self.headers.get('Origin')
            if origin and origin not in tuple('http://' + h for h in hosts):
                raise PermissionError('ORIGIN_DENIED')
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            sid = cookie['s1'].value if 's1' in cookie else None
            return sid if sid in sessions else None

        def do_GET(self):
            try:
                sid = self.admit()
                if self.path == '/api/session':
                    if sid is None:
                        if len(sessions) >= 128:
                            return self.reply(429, dict(error='SESSION_LIMIT'))
                        sid = secrets.token_hex(24)
                        sessions[sid] = secrets.token_hex(24)
                    return self.reply(200, dict(csrf=sessions[sid]), cookie=f's1={sid}; HttpOnly; SameSite=Strict; Path=/')
                if self.path == '/api/health':
                    return self.reply(200, dict(stage='S1', llm_enabled=False, optimization_allowed=False))
                assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css'), '/favicon.ico': ('favicon.svg','image/svg+xml'), '/favicon.svg': ('favicon.svg','image/svg+xml')}
                if self.path in assets:
                    name, mime = assets[self.path]
                    return self.reply(200, (ASSETS / name).read_bytes(), mime)
                if sid is None:
                    raise PermissionError('SESSION_REQUIRED')
                if self.path == '/api/catalog':
                    return self.reply(200, service.catalog())
                if self.path == '/api/contracts':
                    value=json.loads((ASSETS.parent / 'knowledge.json').read_text(encoding='utf-8'))
                    value['claim_schema']=json.loads((ASSETS.parent/'claim_schema_v11.json').read_text(encoding='utf-8'))
                    return self.reply(200,value)
                if self.path.startswith('/api/facts/'):
                    return self.reply(200,service.fact_catalog(self.path.split('/')[-1],sid))
                if self.path.startswith('/api/contexts/'):
                    return self.reply(200, service.get(self.path.split('/')[-1], sid))
                if self.path.startswith('/api/evidence/'):
                    return self.reply(200, service.evidence(self.path.split('/')[-1], sid))
                return self.reply(404, dict(error='ROUTE_UNKNOWN'))
            except PermissionError:
                self.reply(403, dict(error='ACCESS_DENIED'))
            except Exception:
                self.reply(409, dict(error='EVIDENCE_UNAVAILABLE'))

        def do_POST(self):
            try:
                sid = self.admit()
                if sid is None or self.headers.get('X-CSRF-Token') != sessions[sid]:
                    raise PermissionError('CSRF_DENIED')
                if self.path not in ('/api/contexts','/api/claims/resolve'):
                    return self.reply(404, dict(error='ROUTE_UNKNOWN'))
                if self.headers.get('Content-Type') != 'application/json' or self.headers.get('Transfer-Encoding'):
                    return self.reply(400, dict(error='JSON_REQUIRED'))
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096:
                    return self.reply(413, dict(error='BODY_LIMIT'))
                self.connection.settimeout(10)
                def pairs(items):
                    value = {}
                    for k, v in items:
                        if k in value:
                            raise ValueError('DUPLICATE_KEY')
                        value[k] = v
                    return value
                data = json.loads(self.rfile.read(length), object_pairs_hook=pairs)
                if not isinstance(data, dict):
                    raise ValueError('OBJECT_REQUIRED')
                if not guard.acquire(blocking=False):
                    return self.reply(429, dict(error='COMPUTE_BUSY'))
                try:
                    result = service.create(data, sid) if self.path=='/api/contexts' else service.resolve_claims(data,sid)
                finally:
                    guard.release()
                self.reply(201, result)
            except PermissionError:
                self.reply(403, dict(error='ACCESS_DENIED'))
            except (ValueError, TypeError):
                self.reply(400, dict(error='INVALID_REQUEST'))
            except Exception:
                self.reply(409, dict(error='COMPUTATION_UNAVAILABLE'))

    # Binding is the atomic occupancy check; an occupied port raises, never kills or selects another service.
    class ExclusiveServer(ThreadingHTTPServer):
        allow_reuse_address = False
        def server_bind(self):
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()
    return ExclusiveServer(('127.0.0.1', port), Handler)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8769)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    batch = root / 'artifacts/ai_s1_runs' / secrets.token_hex(16)
    # Reserve port before expensive model loads/protection scans.
    server = make_server(None, args.port)
    try:
        check(root, batch / 'protection_start.json')
        service = EvidenceService(batch / 'evidence')
        server.server_close()
        server = make_server(service, args.port)
        print(f'S1 http://127.0.0.1:{args.port} batch={batch}', flush=True)
        server.serve_forever()
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
