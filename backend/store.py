"""All durable application state lives in the project's private SQLite database."""
import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


def ident():
    return uuid.uuid4().hex


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, workspace TEXT NOT NULL, request_id TEXT UNIQUE NOT NULL, body TEXT NOT NULL)')
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def new_workspace(self):
        now = time.time()
        w = {'id': ident(), 'title': '新的空间', 'created': now, 'updated': now,
             'artifacts': [], 'messages': [], 'dataset': None, 'revision': 0}
        with self.lock, self.connect() as db:
            db.execute('INSERT INTO workspaces VALUES (?, ?)', (w['id'], json.dumps(w)))
        return w

    def workspace(self, key):
        with self.connect() as db:
            row = db.execute('SELECT body FROM workspaces WHERE id=?', (key,)).fetchone()
        if not row:
            raise KeyError('工作区不存在')
        return json.loads(row['body'])

    def workspaces(self):
        with self.connect() as db:
            rows = db.execute('SELECT body FROM workspaces').fetchall()
        return sorted([{'id': w['id'], 'title': w['title'], 'updated': w['updated'],
                        'count': len(w['artifacts'])} for w in (json.loads(r['body']) for r in rows)],
                      key=lambda w: w['updated'], reverse=True)

    def mutate(self, key, fn):
        with self.lock, self.connect() as db:
            row = db.execute('SELECT body FROM workspaces WHERE id=?', (key,)).fetchone()
            if not row:
                raise KeyError('工作区不存在')
            w = json.loads(row['body'])
            fn(w)
            w['revision'] += 1
            w['updated'] = time.time()
            db.execute('UPDATE workspaces SET body=? WHERE id=?', (json.dumps(w), key))
            return w

    def put_artifact(self, workspace, artifact):
        # Each run appends a new result. User-edited artifacts are never overwritten.
        artifact = {**artifact, 'id': ident(), 'version': 0, 'pinned': False, 'created': time.time()}
        self.mutate(workspace, lambda w: w['artifacts'].append(artifact))
        return artifact

    def edit_artifact(self, workspace, artifact_id, patch):
        def update(w):
            a = next((a for a in w['artifacts'] if a['id'] == artifact_id), None)
            if not a:
                raise KeyError('内容不存在')
            if patch.get('version') != a['version']:
                raise ValueError('内容已更新，请刷新后再编辑')
            if 'pinned' in patch:
                if type(patch['pinned']) is not bool:
                    raise ValueError('固定状态无效')
                a['pinned'] = patch['pinned']
            if 'text' in patch:
                if a['type'] != 'document' or not isinstance(patch['text'], str) or len(patch['text']) > 100000:
                    raise ValueError('文稿格式无效')
                a['data']['text'] = patch['text']
            if 'task_id' in patch:
                if a['type'] != 'tasks' or type(patch.get('done')) is not bool:
                    raise ValueError('任务状态无效')
                task = next((t for t in a['data']['items'] if t['id'] == patch['task_id']), None)
                if not task:
                    raise KeyError('任务不存在')
                task['done'] = patch['done']
            a['version'] += 1
        return self.mutate(workspace, update)

    def save_job(self, job):
        with self.lock, self.connect() as db:
            db.execute('INSERT INTO jobs VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',
                       (job['id'], job['workspace'], job['request_id'], json.dumps(job)))

    def job(self, key=None, request_id=None):
        with self.connect() as db:
            row = db.execute('SELECT body FROM jobs WHERE ' + ('id=?' if key else 'request_id=?'),
                             (key or request_id,)).fetchone()
        return json.loads(row['body']) if row else None

    def jobs(self, workspace=None):
        with self.connect() as db:
            rows = db.execute('SELECT body FROM jobs' + (' WHERE workspace=?' if workspace else ''),
                              (workspace,) if workspace else ()).fetchall()
        return sorted([json.loads(r['body']) for r in rows], key=lambda j: j['created'], reverse=True)
