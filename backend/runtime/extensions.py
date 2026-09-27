"""Explicit, digest-pinned local extension packages; trusted code, not a sandbox."""
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from .protocol import validate

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / 'protocol/extensions/v0.1'
KINDS = {'component': 'components', 'capability': 'capabilities', 'workflow': 'workflows'}
BUILTINS = {'writer.outline': 'outline', 'writer.notes': 'notes',
            'writer.structure': 'structure', 'writer.references': 'references',
            'writer.images': 'images', 'market.quotes': 'market'}
SCHEMA_KEYS = {'type', 'properties', 'required', 'additionalProperties', 'items', 'enum',
               'const', 'minLength', 'maxLength', 'pattern', 'minimum', 'maximum',
               'minItems', 'maxItems', 'description', 'title', '$schema', '$id'}


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('Duplicate JSON property: ' + key)
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('Nonfinite JSON value: ' + value)
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique, parse_constant=invalid_constant)


def local_file(folder, name):
    """Entries/styles use canonical relative POSIX paths, never URLs or symlinks."""
    path = Path(name)
    if path.is_absolute() or '\\' in name or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Noncanonical package path: ' + name)
    target = folder / path
    if any((folder / Path(*path.parts[:i])).is_symlink() for i in range(1, len(path.parts) + 1)):
        raise ValueError('Package paths cannot contain symlinks')
    if not target.resolve().is_relative_to(folder.resolve()) or not target.is_file():
        raise ValueError('Entry must be an existing package file: ' + name)
    return target


def digest(folder):
    if folder.is_symlink():
        raise ValueError('Module packages cannot be symlinks')
    h = hashlib.sha256()
    total = 0
    for p in sorted(folder.rglob('*')):
        if p.is_symlink():
            raise ValueError('Module packages cannot contain symlinks')
        if '__pycache__' in p.parts or p.suffix == '.pyc':
            continue
        if p.is_file():
            data = p.read_bytes()
            total += len(data)
            if total > 10_000_000:
                raise ValueError('Module package exceeds 10 MB')
            h.update(p.relative_to(folder).as_posix().encode() + b'\0' + str(len(data)).encode() + b'\0' + data)
    return h.hexdigest()


def check_schema(contract):
    """Reject unsupported keywords rather than silently ignoring validation rules."""
    if not isinstance(contract, dict) or set(contract) - SCHEMA_KEYS:
        raise ValueError('Extension schemas must use the documented runtime JSON Schema subset')
    if 'type' in contract and contract['type'] not in ('object', 'array', 'string', 'integer', 'number', 'boolean', 'null'):
        raise ValueError('Unsupported schema type')
    if 'enum' in contract and (not isinstance(contract['enum'], list) or not contract['enum']):
        raise ValueError('enum must be a nonempty array')
    if 'pattern' in contract:
        if not isinstance(contract['pattern'], str): raise ValueError('pattern must be a string')
        re.compile(contract['pattern'])
    for key in ('minimum', 'maximum'):
        if key in contract and (type(contract[key]) not in (int, float) or not math.isfinite(contract[key])):
            raise ValueError('Invalid numeric bound: ' + key)
    if 'properties' in contract:
        if not isinstance(contract['properties'], dict):
            raise ValueError('Schema properties must be an object')
        for child in contract['properties'].values():
            check_schema(child)
    if 'items' in contract:
        check_schema(contract['items'])
    if isinstance(contract.get('additionalProperties'), dict):
        check_schema(contract['additionalProperties'])
    elif 'additionalProperties' in contract and type(contract['additionalProperties']) is not bool:
        raise ValueError('additionalProperties must be a schema or boolean')
    if 'required' in contract and (not isinstance(contract['required'], list) or
                                  any(not isinstance(k, str) for k in contract['required'])):
        raise ValueError('required must be an array of property names')
    for key in ('minItems', 'maxItems', 'minLength', 'maxLength'):
        if key in contract and (type(contract[key]) is not int or contract[key] < 0):
            raise ValueError('Invalid schema bound: ' + key)
    for lower, upper in (('minimum', 'maximum'), ('minItems', 'maxItems'), ('minLength', 'maxLength')):
        if lower in contract and upper in contract and contract[lower] > contract[upper]:
            raise ValueError('Schema lower bound exceeds upper bound')


def package(path, kind):
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError('Module packages cannot contain symlinks')
    m = read(path)
    validate(m, read(CONTRACTS / 'module.schema.json'))
    if m['kind'] != kind or path.parent.name != m['id']:
        raise ValueError('Mismatched package directory: ' + m['id'])
    for key in ('inputSchema', 'outputSchema', 'stateSchema'):
        check_schema(m[key])
    for key in ('provides', 'accepts', 'permissions'):
        if len(set(m[key])) != len(m[key]):
            raise ValueError('Duplicate ' + key)
    if not m['builtin']:
        entry = local_file(path.parent, m['entry'])
        expected = {'component': '.js', 'capability': '.py', 'workflow': '.json'}[kind]
        if entry.suffix != expected:
            raise ValueError('Incorrect entry extension for ' + kind)
    elif kind != 'component' or BUILTINS.get(m['id']) != m.get('slotKey') or m['entry'] != 'builtin:' + m['slotKey']:
        raise ValueError('Only application-owned builtins may bypass installation')
    if 'style' in m:
        if kind != 'component' or local_file(path.parent, m['style']).suffix != '.css':
            raise ValueError('Styles must be component-local CSS files')
    if kind == 'component':
        for key in ('activation', 'placement', 'ports'):
            if key not in m:
                raise ValueError('Missing component ' + key)
        if m['network'] or m['sideEffect'] != 'L0' or m['cost'] != 'none' or m['permissions'] or m['provides']:
            raise ValueError('Components render data; effects belong in governed capabilities')
        if len({p['name'] for p in m['ports']}) != len(m['ports']):
            raise ValueError('Duplicate component port')
    if kind == 'capability':
        if len(m['provides']) != 1:
            raise ValueError('One capability per package')
        if m['inputSchema'].get('type') != 'object' or m['outputSchema'].get('type') != 'object':
            raise ValueError('Capability input and output schemas must describe objects')
        output = m['outputSchema']
        if 'artifacts' not in output.get('required', []) or output.get('properties', {}).get('artifacts', {}).get('type') != 'array':
            raise ValueError('Capability output schema must require an artifacts array')
    if kind == 'workflow':
        validate(read(local_file(path.parent, m['entry'])), read(CONTRACTS / 'batch.schema.json'))
    return m, path.parent, digest(path.parent)


def discover(strict=True):
    result = {}
    for kind, directory in KINDS.items():
        root = ROOT / 'modules' / directory
        if root.is_symlink():
            raise ValueError('Module roots cannot be symlinks')
        for path in sorted(root.glob('*/manifest.json')):
            try:
                m, folder, sha = package(path, kind)
                if m['id'] in result:
                    raise ValueError('Duplicate module ID: ' + m['id'])
                result[m['id']] = m, folder, sha
            except (ValueError, OSError, TypeError, re.error) as exc:
                if strict:
                    raise ValueError(str(path.relative_to(ROOT)) + ': ' + str(exc)) from exc
                print('Extension unavailable: ' + str(path.relative_to(ROOT)) + ': ' + str(exc), file=sys.stderr)
    return result


def installed():
    lock = read(ROOT / 'modules/installed.json')
    if set(lock) != {'version', 'modules'} or lock['version'] != '0.1' or not isinstance(lock['modules'], dict):
        raise ValueError('Invalid modules/installed.json')
    if any(not re.fullmatch(r'[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+', k) or
           not isinstance(v, str) or not re.fullmatch(r'[a-f0-9]{64}', v) for k, v in lock['modules'].items()):
        raise ValueError('Installed modules require exact SHA-256 digests')
    return lock


def enabled(strict=True):
    lock = installed()['modules']
    return [(m, p, d) for m, p, d in discover(strict).values()
            if m['builtin'] or lock.get(m['id']) == d]


def install_capabilities(kernel):
    kernel.extension_errors = []
    try:
        packages = enabled(strict=False)
    except (ValueError, OSError) as exc:
        kernel.extension_errors.append(str(exc))
        print('Extensions unavailable: ' + str(exc), file=sys.stderr)
        return
    for m, folder, sha in packages:
        if m['kind'] != 'capability':
            continue
        try:
            cap = m['provides'][0]
            if cap in kernel.providers or any(p['manifest']['id'] == m['id'] for p in kernel.providers.values()):
                raise ValueError('Extension shadows an existing capability or module: ' + cap)
            if digest(folder) != sha:
                raise ValueError('Package changed while loading')
            name = 'wanjie_extension_' + sha
            loader = importlib.util.spec_from_file_location(name, folder / m['entry'],
                                                          submodule_search_locations=[str(folder)])
            module = importlib.util.module_from_spec(loader)
            sys.modules[name] = module
            try:
                # Compile current source so cached bytecode cannot defeat content pinning.
                exec(compile((folder / m['entry']).read_bytes(), str(folder / m['entry']), 'exec'), module.__dict__)
            except (Exception, SystemExit) as exc:
                for imported in tuple(sys.modules):
                    if imported == name or imported.startswith(name + '.'):
                        sys.modules.pop(imported, None)
                raise ValueError('Module import failed: ' + str(exc)) from exc
            if not callable(getattr(module, 'execute', None)):
                raise ValueError('Capability entry must export execute(task, progress, cancelled)')
            def handler(task, progress, cancel, fn=module.execute, contract=m['outputSchema']):
                output = fn(task, progress, cancel)
                validate(output, contract)
                if not isinstance(output, dict) or not isinstance(output.get('artifacts'), list):
                    raise ValueError('Capability output must contain artifacts array')
                return output
            spec = {k: m[k] for k in ('title', 'inputSchema', 'outputSchema', 'sideEffect', 'permissions', 'network', 'cost', 'reversible')}
            spec.update(id=cap, module=m['id'])
            manifest = {k: m[k] for k in ('id', 'version', 'title', 'provides', 'accepts', 'permissions', 'network', 'cost', 'reversible')}
            manifest.update(protocolVersion='0.1', kind='capability', emits=['result.capability.result'],
                            requires_context=['intent'], side_effect=m['sideEffect'], latency='variable', trusted=True)
            kernel.register(spec, manifest, handler)
        except Exception as exc:
            error = m['id'] + ': ' + str(exc)
            kernel.extension_errors.append(error)
            print('Extension unavailable: ' + error, file=sys.stderr)
