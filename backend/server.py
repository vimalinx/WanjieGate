"""Loopback-only same-origin API and static server. Run: python3 -m backend.server."""
import argparse
import json
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .composition import CAPABILITIES, compose, parse_dataset, analyze
from .providers import Generator, Kev
from .scheduler import Scheduler
from .store import Store
from .live_runtime import LiveRuntime

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
            if path == '/' or path.startswith('/w/'):
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
        store, scheduler, kev = self.server.store, self.server.scheduler, self.server.kev
        if path == '/api/status' and method == 'GET':
            return {'kev': kev.last, 'generator': {**scheduler.generator.last, 'pack': scheduler.generator.pack, 'model': scheduler.generator.model},
                    'active_jobs': sum(j['status'] not in {'complete', 'failed', 'cancelled', 'interrupted'} for j in store.jobs())}
        if path == '/api/workspaces':
            if method == 'GET':
                return {'workspaces': store.workspaces()}
            if method == 'POST':
                return store.new_workspace()
        pending = re.fullmatch(r'/api/submissions/([a-zA-Z0-9-]{16,80})', path)
        if pending and method == 'GET':
            return {'job': store.job(request_id=pending[1])}
        match = re.fullmatch(r'/api/workspaces/([a-f0-9]{32})(?:/(dataset|note|export|jobs|artifacts)(?:/([a-f0-9]{32}))?)?', path)
        if match:
            key, action, item = match.groups()
            w = store.workspace(key)
            if method == 'GET' and not action:
                return {**w, 'jobs': store.jobs(key)[:20]}
            if method == 'GET' and action == 'export':
                parts = ['# ' + w['title']]
                for a in w['artifacts']:
                    parts.append('\n## ' + a['title'])
                    if a['type'] == 'document':
                        parts.append(a['data']['text'])
                    elif a['type'] == 'tasks':
                        parts.extend(f"- [{'x' if t['done'] else ' '}] {t['title']} — {t['detail']}" for t in a['data']['items'])
                    else:
                        parts.append(('演示数据 · ' if a['data']['dataset']['demo'] else '') + a['data']['dataset']['name'])
                        for col in a['data']['columns']:
                            parts.append(f"- {col['name']}: 合计 {col['total']:g}，均值 {col['mean']:g}，最小 {col['min']:g}，最大 {col['max']:g}")
                return {'filename': 'wanjiegate-' + key[:8] + '.md', 'text': '\n\n'.join(parts)}
            if method == 'POST' and action == 'dataset':
                dataset = None if b.get('remove') else parse_dataset(b.get('text'), b.get('name', '粘贴的数据'), b.get('demo', False))
                return store.mutate(key, lambda ws: ws.update(dataset=dataset))
            if method == 'POST' and action == 'note':
                text = valid_text(b.get('text'))
                return store.put_artifact(key, {'type': 'document', 'title': '随手记', 'data': {'text': text}, 'source': '本地笔记'})
            if method == 'PATCH' and action == 'artifacts' and item:
                return store.edit_artifact(key, item, b)
            if method == 'POST' and action == 'jobs':
                text = valid_text(b.get('text'))
                selected = b.get('selected')
                if selected is not None and (not isinstance(selected, list) or not selected or any(not isinstance(k, str) or k not in CAPABILITIES for k in selected)):
                    raise ValueError('能力选择无效')
                request_id = b.get('request_id')
                if not isinstance(request_id, str) or not re.fullmatch(r'[a-zA-Z0-9-]{16,80}', request_id):
                    raise ValueError('需要有效的发送编号')
                return scheduler.submit(key, text, selected, request_id, bool(b.get('local_only')))
        if path == '/api/preview' and method == 'POST':
            text = valid_text(b.get('text'))
            client, revision = b.get('client'), b.get('revision')
            if client is not None:
                self.server.live.observe(client, revision)
            w = store.workspace(b['workspace']) if b.get('workspace') else {'dataset': None, 'artifacts': []}
            context = {'dataset': {'name': w['dataset']['name'], 'columns': w['dataset']['headers']} if w['dataset'] else None,
                       'artifacts': [{'type': a['type'], 'title': a['title']} for a in w['artifacts'][-6:]]}
            scores, decision = kev.decide(text, context)
            plan = compose(text, w['dataset'], scores)
            analysis = analyze(w['dataset']) if w['dataset'] and any(s['id'] == 'analyze' for s in plan['steps']) else None
            content_context = {**context, 'analysis': analysis,
                               'documents': [a['data']['text'][:6000] for a in w['artifacts'][-3:] if a['type'] == 'document']}
            scene = self.server.live.request(client, revision, text, plan, w['dataset'], content_context, scores.get('market'), bool(b.get('local_only'))) if client else None
            return {**plan, 'decision': decision, 'analysis': analysis, 'scene': scene}
        scene_path = re.fullmatch(r'/api/scenes/([a-f0-9-]{32,36})/(\d+|cancel)', path)
        if scene_path:
            client, action = scene_path.groups()
            if method == 'GET' and action.isdigit():
                return self.server.live.snapshot(client, int(action))
            if method == 'POST' and action == 'cancel':
                return self.server.live.cancel(client, b.get('revision'))
        match = re.fullmatch(r'/api/jobs/([a-f0-9]{32})(/cancel)?', path)
        if match:
            job = store.job(match[1])
            if not job:
                raise KeyError('执行不存在')
            if method == 'POST' and match[2]:
                return scheduler.cancel(match[1])
            if method == 'GET' and not match[2]:
                return job
        raise KeyError('接口不存在')

    def log_message(self, fmt, *args):
        # Do not print request bodies or provider credentials.
        if len(args) > 1 and str(args[1]) != '200':
            super().log_message(fmt, *args)


def valid_text(text):
    if not isinstance(text, str) or not text.strip() or len(text) > 12000:
        raise ValueError('请输入 1–12000 字的内容')
    return text.strip()


def create_server(port, data_dir):
    os.umask(0o077)
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.store = Store(Path(data_dir) / 'workspaces.sqlite3')
    server.kev = Kev()
    server.scheduler = Scheduler(server.store, Generator(Path(data_dir) / 'receipts'))
    server.live = LiveRuntime(Generator(Path(data_dir) / 'receipts'))
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
        server.scheduler.pool.shutdown(wait=True)
        server.live.shutdown()


if __name__ == '__main__':
    main()
