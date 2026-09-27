#!/usr/bin/env python3
"""Bounded single-host DAG runner. Default is an offline plan; --run submits once."""
import argparse
from collections import deque
import fcntl
import hashlib
import json
import os
import sys
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.runtime.extensions import ROOT, CONTRACTS, read
from backend.runtime.protocol import validate, message, TERMINAL

FINISHED = TERMINAL | {'skipped'}
UNCERTAIN = {'submitting', 'unknown', 'outcome_unknown'}


def plan(batch):
    validate(batch, read(CONTRACTS / 'batch.schema.json'))
    jobs = {j['id']: j for j in batch['jobs']}
    if len(jobs) != len(batch['jobs']): raise ValueError('Duplicate job ID')
    if len(jobs) > batch['maxSubmissions']: raise ValueError('Submission budget too small')
    pending = {}; children = {id_: [] for id_ in jobs}
    for id_, job in jobs.items():
        if len(set(job['dependsOn'])) != len(job['dependsOn']): raise ValueError('Duplicate dependency: ' + id_)
        pending[id_] = len(job['dependsOn'])
        for dependency in job['dependsOn']:
            if dependency not in jobs: raise ValueError('Missing dependency: ' + dependency)
            children[dependency].append(id_)
    ready = deque(id_ for id_, count in pending.items() if count == 0)
    order = []
    while ready:
        id_ = ready.popleft(); order.append(id_)
        for child in children[id_]:
            pending[child] -= 1
            if pending[child] == 0: ready.append(child)
    if len(order) != len(jobs): raise ValueError('Dependency cycle')
    return jobs, order


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def endpoint(value):
    parsed = urlsplit(value)
    if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or
            parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment or
            parsed.port is None):
        raise ValueError('Batch v0.1 requires http://127.0.0.1:PORT or http://localhost:PORT')
    return value.rstrip('/')


def api(base, path, body=None, timeout=20):
    raw = None if body is None else json.dumps(body, allow_nan=False).encode()
    request = urllib.request.Request(base + '/api/runtime' + path, data=raw,
                                     headers={'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=max(.1, timeout)) as response:
        data = json.load(response)
        if not isinstance(data, dict): raise ValueError('Runtime returned a non-object response')
        return data


def save(path, data):
    tmp = path.with_suffix('.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def accepted(record, response):
    task = response.get('task')
    if isinstance(task, dict) and isinstance(task.get('id'), str) and task.get('status') in TERMINAL | {'queued', 'running'}:
        record.update(task=task['id'], status=task['status'])
    else:
        # A malformed response cannot establish that submission did not happen.
        record.update(status='unknown', error='Unrecognized submission receipt')


def summary(path, journal, jobs):
    states = {k: v['status'] for k, v in journal['jobs'].items()}
    unsubmitted = [k for k in jobs if k not in states]
    success = not unsubmitted and all(v == 'success' for v in states.values())
    uncertain = any(v in UNCERTAIN for v in states.values())
    running = any(v in ('queued', 'running') for v in states.values())
    outcome = 'success' if success else 'unknown' if uncertain else 'pending' if running or unsubmitted else 'failure'
    print(json.dumps({'outcome': outcome, 'journal': str(path), 'jobs': states,
                      'unsubmitted': unsubmitted, 'error': journal.get('lastError')}, ensure_ascii=False, indent=2))
    return {'success': 0, 'failure': 2, 'pending': 3, 'unknown': 4}[outcome]


def run(batch, jobs, order, base):
    fingerprint = hashlib.sha256(json.dumps(batch, sort_keys=True, allow_nan=False).encode()).hexdigest()
    directory = ROOT / '.data/batches' / batch['id']
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.is_symlink(): raise ValueError('Batch journal cannot be a symlink')
    os.chmod(directory, 0o700)
    with open(directory / 'lock', 'a') as lock:
        os.chmod(directory / 'lock', 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = directory / 'journal.json'
        if path.is_symlink(): raise ValueError('Batch journal cannot be a symlink')
        journal = read(path) if path.exists() else {'version': '0.1', 'digest': fingerprint, 'base': base,
                                                  'createdAt': int(time.time()), 'jobs': {}}
        if journal['digest'] != fingerprint or journal['base'] != base:
            raise ValueError('Resume requires identical batch and endpoint; never change a journal to force replay')
        if set(journal['jobs']) - set(jobs): raise ValueError('Journal contains unknown jobs')
        journal.pop('lastError', None)
        validated = False
        deadline = time.monotonic() + batch['timeoutSeconds']
        def request(route, body=None):
            if time.monotonic() >= deadline: raise TimeoutError('Batch invocation deadline reached')
            return api(base, route, body, min(20, deadline - time.monotonic()))
        try:
            state = request('/intents/' + batch['intent'])
            caps = {c['id']: c for c in state['capabilities']}
            for job in jobs.values():
                if job['capability'] not in caps: raise ValueError('Unknown capability: ' + job['capability'])
                validate(job['input'], caps[job['capability']]['inputSchema'])
            validated = True
            save(path, journal)
            while time.monotonic() < deadline:
                state = request('/intents/' + batch['intent'])
                tasks = {t['id']: t for t in state['tasks']}
                for record in journal['jobs'].values():
                    if record['status'] in ('submitting', 'unknown'):
                        prior = request('/commands/' + record['command']['id'])
                        if prior.get('found'): accepted(record, prior['response'])
                        else: record['status'] = 'unknown'
                    if record.get('task') in tasks:
                        task = tasks[record['task']]
                        record.update(status=task['status'], artifacts=task.get('artifacts', []))
                        if task.get('error'): record['error'] = task['error']
                save(path, journal)
                # Unknown outcomes stop the whole batch. No automatic POST replay.
                if any(r['status'] in UNCERTAIN for r in journal['jobs'].values()): break
                live = sum(r['status'] not in FINISHED for r in journal['jobs'].values())
                occupied = sum(t['status'] not in TERMINAL for t in state['tasks'])
                for id_ in order:
                    if id_ in journal['jobs']: continue
                    job = jobs[id_]
                    deps = [journal['jobs'].get(d, {}).get('status') for d in job['dependsOn']]
                    if any(s in FINISHED and s != 'success' for s in deps):
                        journal['jobs'][id_] = {'status': 'skipped', 'reason': 'dependency_not_successful'}
                        continue
                    if any(s != 'success' for s in deps): continue
                    if live >= batch['maxParallel'] or occupied >= 3: break
                    command = message('command', 'capability.run',
                                      {'capability': job['capability'], 'input': job['input']},
                                      source='renderer', intent=batch['intent'])
                    command['idempotencyKey'] = command['id']
                    record = {'status': 'submitting', 'command': command}
                    journal['jobs'][id_] = record
                    # Write-ahead record is durable before crossing the HTTP boundary.
                    save(path, journal)
                    try:
                        response = request('/commands', command)
                        accepted(record, response)
                        if record['status'] not in FINISHED: live += 1; occupied += 1
                    except urllib.error.HTTPError as exc:
                        # Only 4xx establishes rejection for this local runtime contract.
                        record.update(status='failure' if 400 <= exc.code < 500 else 'unknown',
                                      error='HTTP ' + str(exc.code))
                    except (OSError, ValueError):
                        record.update(status='unknown', error='Submission response unavailable; reconcile only')
                    save(path, journal)
                    if record['status'] in UNCERTAIN: break
                save(path, journal)
                if any(r['status'] in UNCERTAIN for r in journal['jobs'].values()): break
                if len(journal['jobs']) == len(jobs) and all(r['status'] in FINISHED for r in journal['jobs'].values()): break
                time.sleep(min(.5, max(0, deadline - time.monotonic())))
        except (OSError, ValueError, KeyError) as exc:
            if not validated and isinstance(exc, (ValueError, KeyError)):
                raise
            journal['lastError'] = str(exc)
            save(path, journal)
        except KeyboardInterrupt:
            journal['lastError'] = 'Client interrupted; accepted runtime tasks continue. Resume to reconcile.'
            save(path, journal)
        return summary(path, journal, jobs)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('file', type=Path); p.add_argument('--run', action='store_true')
    p.add_argument('--base', default='http://127.0.0.1:5174'); a = p.parse_args()
    base = endpoint(a.base)
    batch = read(a.file); jobs, order = plan(batch)
    if not a.run:
        print(json.dumps({'plan': order, 'maxParallel': batch['maxParallel'], 'submissions': len(jobs),
                          'executed': False, 'inputValidation': 'batch contract only; capability schemas checked on --run'}, indent=2))
        return 0
    return run(batch, jobs, order, base)


if __name__ == '__main__':
    try: sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr); sys.exit(2)
