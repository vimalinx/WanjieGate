"""Context-local relations over stable Artifacts; queries never grant authority."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from .protocol import Fault, validate

CONTRACT = Path(__file__).resolve().parents[2] / 'protocol/extensions/v0.1/context-relation.schema.json'
DEFAULT_ROLE = 'context'


def relation_id(intent, artifact, role=DEFAULT_ROLE):
    if role == DEFAULT_ROLE:
        return intent + ':' + artifact  # Preserve existing member IDs.
    return 'context-relation:' + hashlib.sha256(json.dumps([intent, artifact, role]).encode()).hexdigest()


def normalize(member):
    """Read compatibility only: never rewrite legacy rows or infer shared grants."""
    m = deepcopy(member)
    m.setdefault('role', DEFAULT_ROLE)
    m.setdefault('relevance', .5)
    m.setdefault('state', 'active')
    m.setdefault('localProperties', {})
    # Legacy semantic rows cannot become explicit cross-space grants.
    m.setdefault('origin', 'computed' if m.get('reason') in ('语义相关性', '当前产生或导入') else 'explicit')
    m.setdefault('pinned', False)
    m.setdefault('tier', 'WARM')
    m.setdefault('detail', 'full')
    return m


def stored_relations(tx, intent):
    return [normalize(m) for m in tx.list('member', intent)]


def accessible(tx, intent):
    artifacts = {a['id']: a for a in tx.list('artifact')}
    result = {key: a for key, a in artifacts.items() if a['intent'] == intent}
    for m in stored_relations(tx, intent):
        a = artifacts.get(m['artifact'])
        if a and a['scope'] == 'shared' and m['origin'] == 'explicit' and m['state'] == 'active':
            result[a['id']] = a
    return result


def protected(tx, intent, artifact, role=DEFAULT_ROLE):
    """Explicit tombstones also prevent automatic resurrection of the same role."""
    return any(m['artifact'] == artifact and (m['pinned'] or
               (m['role'] == role and m['origin'] == 'explicit'))
               for m in stored_relations(tx, intent))


def _changed(tx, intent):
    # Invalidate in-flight semantic proposals after local membership changes.
    tx.put(tx.get(intent, 'intent'))


def set_relation(tx, intent, payload, cause, principal):
    p = deepcopy(payload)
    role = p.get('role', DEFAULT_ROLE)
    origin = p.get('origin', 'explicit')
    if origin == 'explicit' and principal != 'human':
        raise Fault('permission_denied', '只有显式用户操作可建立显式引用')
    a = tx.get(p['artifact'], 'artifact')
    mid = relation_id(intent, a['id'], role)
    try:
        before = normalize(tx.get(mid, 'member'))
    except Fault:
        before = None
    if a['intent'] != intent:
        if a['scope'] != 'shared':
            raise Fault('scope_denied', '内容未共享到其他意图')
        if origin != 'explicit' and a['id'] not in accessible(tx, intent):
            raise Fault('scope_denied', '计算关系不能建立跨空间访问权')
    if origin == 'computed':
        if a.get('pinned') or protected(tx, intent, a['id'], role):
            raise Fault('protected_relation', '计算关系不能覆盖显式或固定关系')
        if p.get('pinned'):
            raise Fault('permission_denied', '计算关系不能自动固定对象')
    m = before or {'id': mid, 'type': 'member', 'intent': intent, 'artifact': a['id'],
                   'role': role, 'tier': 'WARM', 'relevance': .5, 'pinned': False,
                   'state': 'active', 'localProperties': {}, 'detail': 'full'}
    if (p.get('state', m['state']) != 'active' or p.get('tier', m['tier']) == 'COLD') and (a.get('pinned') or m['pinned']) and p.get('pinned') is not False:
        raise Fault('pinned', '请先取消固定')
    m = {**m, **p, 'origin': origin, 'reason': '用户选择' if origin == 'explicit' else '语义相关性'}
    # Validate defaults and requested fields before persistence adds timestamps.
    contract = json.loads(CONTRACT.read_text())
    validate(m, contract)
    saved = tx.put(m, create=before is None)
    tx.emit('context.relation.changed', {'relation': saved, 'before': before}, intent, cause)
    tx.emit('context.changed', {'member': saved}, intent, cause)
    _changed(tx, intent)
    return saved


def remove_relation(tx, intent, payload, cause, principal):
    mid = relation_id(intent, payload['artifact'], payload.get('role', DEFAULT_ROLE))
    if principal != 'human':
        raise Fault('permission_denied', '只有显式用户操作可移除引用')
    try:
        before = normalize(tx.get(mid, 'member'))
        create = False
    except Fault:
        before = next((m for m in effective_relations(tx, intent) if m['id'] == mid), None)
        if before is None:
            raise Fault('not_found', '引用不存在')
        create = True
    if before['pinned']:
        raise Fault('pinned', '请先取消固定')
    # Removal remains possible after the owner revokes sharing. Keep a tombstone.
    value = {k: v for k, v in before.items() if k != 'query'}
    saved = tx.put({**value, 'origin': 'explicit', 'state': 'removed', 'reason': '用户移除'}, create=create)
    tx.emit('context.relation.changed', {'relation': saved, 'before': before}, intent, cause)
    tx.emit('context.changed', {'member': saved}, intent, cause)
    _changed(tx, intent)
    return saved


def set_query(tx, intent, payload, cause, principal, remove=False):
    if principal != 'human':
        raise Fault('permission_denied', '查询定义只能由用户修改')
    key = 'context-query:' + hashlib.sha256(json.dumps([intent, payload['query']]).encode()).hexdigest()
    try:
        before = tx.get(key, 'contextQuery')
    except Fault:
        before = None
    if remove and before is None:
        raise Fault('not_found', '查询不存在')
    value = {**(before or {}), **payload, 'id': key, 'type': 'contextQuery', 'intent': intent,
             'state': 'removed' if remove else 'active'}
    value.setdefault('filter', {})
    value.setdefault('role', DEFAULT_ROLE)
    value.setdefault('relevance', .5)
    value.setdefault('localProperties', {})
    value.setdefault('tier', 'WARM')
    value.setdefault('detail', 'full')
    value = tx.put(value, create=before is None)
    tx.emit('context.query.changed', {'query': value, 'before': before}, intent, cause)
    _changed(tx, intent)
    return value


def _matches(a, relations, filters):
    if filters.get('kinds') and a['kind'] not in filters['kinds']:
        return False
    if 'titleContains' in filters and filters['titleContains'].casefold() not in a['title'].casefold():
        return False
    if 'source' in filters and a['source'] != filters['source']:
        return False
    own = [m for m in relations if m['artifact'] == a['id'] and m['state'] == 'active']
    if filters.get('roles') and not any(m['role'] in filters['roles'] for m in own):
        return False
    if 'minRelevance' in filters and not any(m['relevance'] >= filters['minRelevance'] for m in own):
        return False
    return True


def effective_relations(tx, intent):
    allowed = accessible(tx, intent)
    stored = stored_relations(tx, intent)
    result = {(m['artifact'], m['role']): m for m in stored if m['artifact'] in allowed}
    # Explicit and pinned rows (including tombstones) win. Persisted computed
    # rows win over queries; queries have stable lexical tie-breaking.
    for q in sorted(tx.list('contextQuery', intent), key=lambda q: q['id']):
        if q['state'] != 'active':
            continue
        for a in allowed.values():
            key = (a['id'], q['role'])
            if key in result or a.get('pinned') or any(m['artifact'] == a['id'] and m['pinned'] for m in stored):
                continue
            if _matches(a, stored, q['filter']):
                result[key] = {'id': relation_id(intent, a['id'], q['role']), 'type': 'member',
                    'intent': intent, 'artifact': a['id'], 'role': q['role'], 'origin': 'computed',
                    'state': 'active', 'pinned': False, 'relevance': q['relevance'],
                    'localProperties': deepcopy(q['localProperties']), 'tier': q['tier'], 'detail': q['detail'],
                    'reason': '查询匹配', 'query': q['id']}
    return [m for m in result.values() if m['state'] == 'active']


def primary_members(tx, intent):
    """Legacy working-set representation, deterministic across multiple roles."""
    result = {}
    relations = effective_relations(tx, intent)
    for m in sorted(relations, key=lambda m: (
            not m['pinned'], m['origin'] != 'explicit', {'HOT': 0, 'WARM': 1, 'COLD': 2}[m['tier']],
            -m['relevance'], m['role'] != DEFAULT_ROLE, m['id'])):
        result.setdefault(m['artifact'], deepcopy(m))
    for artifact, member in result.items():
        explicit = [m for m in relations if m['artifact'] == artifact and m['origin'] == 'explicit']
        # A second role or computed query cannot widen an explicit read limit.
        if explicit:
            member['detail'] = max((m['detail'] for m in explicit),
                                   key={'full': 0, 'excerpt': 1, 'metadata': 2}.get)
    return result


def snapshot(tx, intent):
    rows = stored_relations(tx, intent)
    effective = effective_relations(tx, intent)
    return {'version': '0.1', 'relations': effective, 'storedRelations': rows,
            'explicitSet': [m for m in effective if m['origin'] == 'explicit'],
            'queries': tx.list('contextQuery', intent)}
