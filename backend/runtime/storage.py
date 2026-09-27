"""Atomic entity projections and append-only message log in the existing SQLite file."""
from contextlib import contextmanager
import json
import sqlite3
import threading
from .protocol import Fault, now, uid, message, validate_message


def dump(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))

class Database:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        with self.transaction() as tx:
            tx.db.executescript('''
                CREATE TABLE IF NOT EXISTS rt_entities (id TEXT PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS rt_entities_kind ON rt_entities(kind);
                CREATE TABLE IF NOT EXISTS rt_messages (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, intent TEXT, correlation TEXT, body TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS rt_messages_intent ON rt_messages(intent,seq);
                CREATE TABLE IF NOT EXISTS rt_commands (key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, response TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS rt_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            ''')

    @contextmanager
    def transaction(self):
        with self.lock:
            db = sqlite3.connect(self.path, timeout=15)
            db.row_factory = sqlite3.Row
            try:
                db.execute('BEGIN IMMEDIATE')
                yield Transaction(db)
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()

    def get(self, key, kind=None):
        with self.transaction() as tx: return tx.get(key, kind)

    def list(self, kind, intent=None):
        with self.transaction() as tx: return tx.list(kind, intent)

    def events(self, after=0, intent=None, correlation=None, limit=200):
        with self.transaction() as tx:
            conditions=['seq>?']; args=[after]
            if intent: conditions.append('intent=?'); args.append(intent)
            if correlation: conditions.append('correlation=?'); args.append(correlation)
            args.append(min(500,max(1,limit)))
            rows=tx.db.execute('SELECT seq,body FROM rt_messages WHERE '+' AND '.join(conditions)+' ORDER BY seq LIMIT ?',args).fetchall()
            return [{**json.loads(r['body']),'seq':r['seq']} for r in rows]

class Transaction:
    def __init__(self, db): self.db=db
    def get(self, key, kind=None):
        row=self.db.execute('SELECT kind,body FROM rt_entities WHERE id=?',(key,)).fetchone()
        if not row or (kind and row['kind'] != kind): raise Fault('not_found','对象不存在')
        return json.loads(row['body'])
    def list(self, kind, intent=None):
        values=[json.loads(r['body']) for r in self.db.execute('SELECT body FROM rt_entities WHERE kind=? ORDER BY rowid',(kind,))]
        return [v for v in values if intent is None or v.get('intent')==intent]
    def put(self, entity, create=False):
        value=dict(entity)
        value['updated']=now()
        if create:
            value.setdefault('id',uid()); value.setdefault('created',now()); value.setdefault('version',0)
            self.db.execute('INSERT INTO rt_entities VALUES (?,?,?)',(value['id'],value['type'],dump(value)))
        else:
            value['version']=value.get('version',0)+1
            if not self.db.execute('UPDATE rt_entities SET body=? WHERE id=?',(dump(value),value['id'])).rowcount:
                raise Fault('not_found','对象不存在')
        return value
    def remove(self,key): self.db.execute('DELETE FROM rt_entities WHERE id=?',(key,))
    def append(self,msg):
        validate_message(msg)
        seq=self.db.execute('INSERT INTO rt_messages(id,intent,correlation,body) VALUES (?,?,?,?)',
                            (msg['id'],msg.get('intent'),msg.get('correlationId'),dump(msg))).lastrowid
        return {**msg,'seq':seq}
    def emit(self,type_,payload,intent=None,cause=None,kind='event',source='kernel',**extra):
        return self.append(message(kind,type_,payload,source,intent,cause,**extra))
    def meta(self,key,default=None):
        row=self.db.execute('SELECT value FROM rt_meta WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else default
    def set_meta(self,key,value):
        self.db.execute('INSERT INTO rt_meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,dump(value)))
