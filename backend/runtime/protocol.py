"""Small JSON Schema subset shared by published contracts and the runtime."""
import json
import math
import re
import time
import uuid
from pathlib import Path

VERSION = '0.2'
ROOT = Path(__file__).resolve().parents[2] / 'protocol' / 'v0.2'
KINDS = ('event', 'signal', 'command', 'result')
RELATIONS = ('belongs_to', 'references', 'produced_by', 'depends_on', 'supports', 'conflicts_with', 'derived_from')
DIMENSIONS = ('thread', 'goal', 'domain', 'phase', 'target', 'attention', 'commitment', 'urgency')
TERMINAL = {'success', 'failure', 'partial', 'cancelled', 'interrupted', 'outcome_unknown'}

class Fault(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)

def uid():
    return uuid.uuid4().hex

def now():
    return int(time.time() * 1000)

def validate(value, schema, path='$'):
    if '$ref' in schema:
        name = schema['$ref']
        if not re.fullmatch(r'[a-z-]+\.schema\.json', name):
            raise Fault('invalid_schema', 'Unsupported schema reference')
        return validate(value, json.loads((ROOT / 'schemas' / name).read_text()), path)
    if 'const' in schema and value != schema['const']:
        raise Fault('invalid_payload', f'{path}: expected {schema["const"]}')
    if 'enum' in schema and value not in schema['enum']:
        raise Fault('invalid_payload', f'{path}: unsupported value')
    kind = schema.get('type')
    good = {'object': isinstance(value, dict), 'array': isinstance(value, list),
            'string': isinstance(value, str), 'integer': type(value) is int,
            'number': type(value) in (int, float) and math.isfinite(value),
            'boolean': type(value) is bool, 'null': value is None}
    if kind and not good.get(kind, False):
        raise Fault('invalid_payload', f'{path}: expected {kind}')
    if isinstance(value, dict):
        for key in schema.get('required', []):
            if key not in value: raise Fault('invalid_payload', f'{path}.{key}: required')
        properties = schema.get('properties', {})
        for key, child in value.items():
            if key in properties: validate(child, properties[key], path + '.' + key)
            elif schema.get('additionalProperties') is False:
                raise Fault('invalid_payload', f'{path}.{key}: unknown field')
            elif isinstance(schema.get('additionalProperties'), dict):
                validate(child, schema['additionalProperties'], path + '.' + key)
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', 10000):
            raise Fault('invalid_payload', f'{path}: array length')
        for i, child in enumerate(value): validate(child, schema.get('items', {}), f'{path}[{i}]')
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', 200000):
            raise Fault('invalid_payload', f'{path}: text length')
        if 'pattern' in schema and re.search(schema['pattern'], value) is None:
            raise Fault('invalid_payload', f'{path}: invalid format')
    if type(value) in (int, float):
        if not math.isfinite(value) or value < schema.get('minimum', -math.inf) or value > schema.get('maximum', math.inf):
            raise Fault('invalid_payload', f'{path}: number out of bounds')
    return value

def schema(name):
    return json.loads((ROOT / 'schemas' / f'{name}.schema.json').read_text())

def message(kind, type_, payload, source='kernel', intent=None, cause=None, **extra):
    result = {'protocolVersion': VERSION, 'id': uid(), 'kind': kind, 'type': type_,
              'timestamp': now(), 'source': source, 'payload': payload, **extra}
    if intent: result['intent'] = intent
    if cause:
        result['correlationId'] = cause.get('correlationId', cause['id'])
        result['causationId'] = cause['id']
    else: result['correlationId'] = result['id']
    validate(result, schema('message'))
    return result

def validate_message(msg):
    validate(msg,schema('message'))
    if msg['kind']=='command':
        contracts=json.loads((ROOT/'commands.json').read_text())
        if msg['type'] not in contracts:raise Fault('unknown_command','未知命令类型')
        validate(msg['payload'],contracts[msg['type']])
    elif msg['kind']=='event':
        contracts=json.loads((ROOT/'events.json').read_text())
        if msg['type'] not in contracts:raise Fault('unknown_event','未知事件类型')
        validate(msg['payload'],contracts[msg['type']])
    elif msg['kind']=='signal':
        validate(msg['payload'],schema('signal'))
        if msg['type']!=msg['payload']['name']:raise Fault('invalid_signal','信号类型与名称不一致')
    else:
        if msg['type'] not in ('command.completed','capability.result'):raise Fault('invalid_result','未知结果类型')
        validate(msg['payload'],schema('result'))
    return msg
