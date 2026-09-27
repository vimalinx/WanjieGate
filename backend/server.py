"""Loopback-only same-origin API and static server. Run: python3 -m backend.server."""
import argparse
import json
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .providers import Generator, Kev
from .store import Store
from .runtime import Kernel
from .runtime.protocol import Fault, ROOT as PROTOCOL_ROOT

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'static'), **kwargs)

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        super().end_headers()

    def allowed_host(self):
        return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

    def send_json(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if not self.allowed_host():
            return self.send_json({'error': 'Host not allowed'}, 403)
        path = urlsplit(self.path).path
        if not path.startswith('/api/'):
            if path in ('/demo', '/demo/'):
                self.path = '/demo.html'
            elif path == '/' or path.startswith('/w/'):
                self.path = '/index.html'
            return super().do_GET()
        self.dispatch('GET', path)

    def do_POST(self):
        self.dispatch('POST', urlsplit(self.path).path)

    def do_PATCH(self):
        self.dispatch('PATCH', urlsplit(self.path).path)

    def dispatch(self, method, path):
        try:
            if not self.allowed_host():
                return self.send_json({'error': 'Host not allowed'}, 403)
            b = {}
            if method != 'GET':
                expected = f'http://{self.headers.get("Host")}'
                if self.headers.get('Origin', expected) != expected or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                    return self.send_json({'error': 'Cross-origin request denied'}, 403)
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    return self.send_json({'error': 'JSON required'}, 415)
                size = int(self.headers.get('Content-Length', '0'))
                if size < 0 or size > 300000:
                    return self.send_json({'error': '请求过大'}, 413)
                b = json.loads(self.rfile.read(size) or b'{}')
                if not isinstance(b, dict):
                    raise ValueError('请求应为对象')
            result = self.route(method, path, b)
            self.send_json(result)
        except Fault as exc:
            self.send_json({'error': str(exc), 'code': exc.code}, 409 if exc.code in {'revision_conflict', 'idempotency_conflict'} else 403 if exc.code in {'permission_required', 'permission_denied', 'scope_denied', 'local_only', 'source_denied'} else 400)
        except KeyError as exc:
            self.send_json({'error': str(exc).strip("'")}, 404)
        except (ValueError, TypeError) as exc:
            self.send_json({'error': str(exc) or '请求格式无效'}, 400)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            import traceback
            traceback.print_exc()
            self.send_json({'error': '服务暂时无法处理请求'}, 500)

    def route(self, method, path, b):
        kernel = self.server.kernel
        if path == '/api/runtime/commands' and method == 'POST':
            return kernel.execute(b)
        submitted = re.fullmatch(r'/api/runtime/commands/([a-zA-Z0-9_-]{1,160})', path)
        if submitted and method == 'GET':
            with kernel.db.transaction() as tx:
                row = tx.db.execute('SELECT response FROM rt_commands WHERE key=?', ('human:' + submitted[1],)).fetchone()
                return {'found': bool(row), 'response': json.loads(row[0]) if row else None}
        if path == '/api/runtime/state' and method == 'GET':
            return kernel.snapshot()
        runtime_state = re.fullmatch(r'/api/runtime/intents/([a-f0-9]{32})', path)
        if runtime_state and method == 'GET':
            return kernel.snapshot(runtime_state[1])
        bus = re.fullmatch(r'/api/runtime/messages/(\d+)(?:/([a-f0-9]{32}))?', path)
        if bus and method == 'GET':
            messages = kernel.db.events(int(bus[1]), bus[2])
            return {'messages': messages, 'cursor': messages[-1]['seq'] if messages else int(bus[1])}
        trace = re.fullmatch(r'/api/runtime/trace/([a-zA-Z0-9_-]{1,160})', path)
        if trace and method == 'GET':
            return {'messages': kernel.db.events(correlation=trace[1], limit=500)}
        contract = re.fullmatch(r'/api/runtime/schema/([a-z-]+)', path)
        if contract and method == 'GET':
            target = PROTOCOL_ROOT / 'schemas' / (contract[1] + '.schema.json')
            if not target.is_file():
                raise KeyError('协议不存在')
            return json.loads(target.read_text())
        if method != 'GET':
            raise Fault('legacy_read_only', '旧接口仅保留读取；请通过 Intent Runtime Command 执行')
        store = self.server.store
        if path == '/api/status':
            return {'protocolVersion': '0.1', 'generator': self.server.scheduler.generator.last,
                    'active_jobs': sum(t['status'] in ('queued', 'running') for t in kernel.db.list('task'))}
        if path == '/api/workspaces':
            return {'workspaces': store.workspaces(), 'readOnly': True}
        legacy = re.fullmatch(r'/api/workspaces/([a-f0-9]{32})', path)
        if legacy:
            return {**store.workspace(legacy[1]), 'jobs': store.jobs(legacy[1]), 'readOnly': True}
        job = re.fullmatch(r'/api/jobs/([a-f0-9]{32})', path)
        if job:
            result = store.job(job[1])
            if result: return result
        pending = re.fullmatch(r'/api/submissions/([a-zA-Z0-9-]{16,80})', path)
        if pending:
            return {'job': store.job(request_id=pending[1])}
        raise KeyError('接口不存在')

    def log_message(self, fmt, *args):
        # Do not print request bodies or provider credentials.
        if len(args) > 1 and str(args[1]) != '200':
            super().log_message(fmt, *args)


def create_server(port, data_dir):
    os.umask(0o077)
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.store = Store(Path(data_dir) / 'workspaces.sqlite3')
    with server.store.connect() as db:
        migrated = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rt_entities'").fetchone()
        has_legacy = db.execute('SELECT 1 FROM workspaces LIMIT 1').fetchone()
        if has_legacy and not migrated:
            import sqlite3
            import time
            backup_dir = Path(data_dir) / 'backups'
            backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            backup_path = backup_dir / ('before-intent-runtime-' + str(time.time_ns()) + '.sqlite3')
            with sqlite3.connect(backup_path) as backup:
                db.backup(backup)
            backup_path.chmod(0o600)
    server.kev = Kev()
    # Legacy objects are read-only adapters; no second execution pool is started.
    from types import SimpleNamespace
    generator = Generator(Path(data_dir) / 'receipts')
    server.scheduler = SimpleNamespace(generator=generator)
    server.kernel = Kernel(server.store, generator)
    if os.environ.get('WANJIE_DEMO') == '1':
        from .bubble_providers import load_config, JevClient, OpenRouterGenerator
        from .runtime.bubbles import install_bubbles
        config = load_config()
        install_bubbles(server.kernel, JevClient(config), OpenRouterGenerator(config))
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5173)
    parser.add_argument('--data-dir', default=str(ROOT / '.data'))
    args = parser.parse_args()
    server = create_server(args.port, args.data_dir)
    print(f'WanjieGate http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.kernel.shutdown()


if __name__ == '__main__':
    main()
