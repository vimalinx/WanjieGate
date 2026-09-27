#!/usr/bin/env python3
"""Module authoring and deterministic packaging; no provider calls."""
import argparse
import fcntl
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.runtime.extensions import ROOT, KINDS, discover, enabled, installed, digest


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name + '-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def catalog():
    modules = []
    for m, folder, sha in enabled():
        if m['kind'] != 'component': continue
        item = {**m, 'digest': sha}
        if not m['builtin']:
            parent = ROOT / 'static/extensions/packages' / m['id']
            target = parent / sha
            parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if digest(target) != sha:
                    raise ValueError('Published bundle differs from digest: ' + str(target))
            else:
                temporary = Path(tempfile.mkdtemp(dir=parent, prefix='.staging-'))
                try:
                    shutil.copytree(folder, temporary, dirs_exist_ok=True,
                                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                    if digest(temporary) != sha: raise ValueError('Package changed during catalog build')
                    os.replace(temporary, target)
                finally:
                    if temporary.exists(): shutil.rmtree(temporary)
            prefix = '/extensions/packages/' + m['id'] + '/' + sha + '/'
            item['entry'] = prefix + m['entry']
            if 'style' in m: item['style'] = prefix + m['style']
        modules.append(item)
    write(ROOT / 'static/extensions/catalog.json', {'version': '0.1', 'modules': modules})
    print('catalog:', len(modules), 'components')


def scaffold(kind, id_):
    if not re.fullmatch(r'[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+', id_) or len(id_) > 160:
        raise ValueError('Use a namespaced lowercase ID, e.g. notes.counter')
    if id_ in discover(): raise ValueError('Module ID already exists: ' + id_)
    folder = ROOT / 'modules' / KINDS[kind] / id_
    folder.mkdir(parents=True, exist_ok=False)
    m = dict(id=id_, version='0.1.0', apiVersion='0.1', title=id_,
             description='Describe the object and when it is useful.', owner='local', kind=kind,
             builtin=False, entry={'component': 'index.js', 'capability': 'provider.py', 'workflow': 'batch.json'}[kind],
             accepts=[], provides=[], permissions=[], sideEffect='L0', network=False, cost='none', reversible=True,
             inputSchema={'type': 'object'}, outputSchema={'type': 'object'}, stateSchema={'type': 'object'})
    if kind == 'component':
        m.update(placement='right', activation={'signal': id_, 'cue': 'Is a character count helpful for the current document?',
                                                'threshold': .75, 'minimumCharacters': 80}, ports=[])
        (folder / 'index.js').write_text("export function mount(root, context) {\n  const count = document.createElement('p'); root.append(count);\n  return {\n    update(input) { count.textContent = input.text.length + ' 字符'; },\n    dispose() { count.remove(); }\n  };\n}\n", encoding='utf-8')
    elif kind == 'capability':
        m['provides'] = [id_]
        m['inputSchema'] = {'type': 'object', 'properties': {'text': {'type': 'string', 'maxLength': 12000}},
                            'required': ['text'], 'additionalProperties': False}
        item = {'type': 'object', 'properties': {'kind': {'const': 'note'}, 'title': {'type': 'string', 'maxLength': 200},
                'content': {'type': 'object', 'properties': {'text': {'type': 'string', 'maxLength': 12000}},
                            'required': ['text'], 'additionalProperties': False},
                'source': {'type': 'string', 'maxLength': 300}},
                'required': ['kind', 'title', 'content', 'source'], 'additionalProperties': False}
        m['outputSchema'] = {'type': 'object', 'properties': {'artifacts': {'type': 'array', 'items': item, 'maxItems': 30}},
                             'required': ['artifacts'], 'additionalProperties': False}
        (folder / 'provider.py').write_text("def execute(task, progress, cancelled):\n    if cancelled():\n        from backend.runtime.protocol import Fault\n        raise Fault('cancelled', 'Task cancelled')\n    text = task['input']['text']\n    return {'artifacts': [{'kind': 'note', 'title': '字符统计', 'content': {'text': str(len(text))}, 'source': 'local:character-count'}]}\n", encoding='utf-8')
    else:
        write(folder / 'batch.json', dict(version='0.1', id=id_.replace('.', '-'), intent='0' * 32,
              maxParallel=2, maxSubmissions=10, timeoutSeconds=300,
              jobs=[{'id': 'read-memory', 'capability': 'memory.retrieve', 'input': {'query': '当前项目'}, 'dependsOn': []}]))
    write(folder / 'manifest.json', m)
    print(folder)
    print('Disabled until explicit install; edit and run module check first.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('check'); sub.add_parser('list'); sub.add_parser('catalog')
    n = sub.add_parser('new'); n.add_argument('kind', choices=KINDS); n.add_argument('id')
    for name in ('install', 'uninstall'):
        s = sub.add_parser(name); s.add_argument('id')
    a = p.parse_args()
    # Serialize authoring/catalog writers. Lock lives outside published packages.
    lock_dir = ROOT / '.data/extensions'; lock_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(lock_dir / 'authoring.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if a.action == 'new': scaffold(a.kind, a.id); return
        packages = discover()
        if a.action == 'check':
            installed()
            print('Valid packages:', len(packages)); return
        if a.action == 'list':
            lock = installed()['modules']
            for m, _, sha in packages.values():
                print(m['id'], m['kind'], m['version'], 'builtin' if m['builtin'] else
                      'installed' if lock.get(m['id']) == sha else 'disabled/changed', sha)
            return
        if a.action in ('install', 'uninstall'):
            if a.id not in packages and a.action == 'install': raise ValueError('Unknown module: ' + a.id)
            if a.id in packages and packages[a.id][0]['builtin']: raise ValueError('Builtins are managed by the application')
            lock = installed()
            if a.action == 'install': lock['modules'][a.id] = packages[a.id][2]
            else: lock['modules'].pop(a.id, None)
            write(ROOT / 'modules/installed.json', lock)
        catalog()


if __name__ == '__main__':
    try: main()
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(str(exc), file=sys.stderr); sys.exit(1)
