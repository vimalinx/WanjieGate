"""Typed capabilities and deterministic dependency planning; no execution here."""
import csv
import io
import json
import math
import re
from pathlib import Path

REGISTRY = json.loads((Path(__file__).resolve().parents[1] / 'static/registry.json').read_text())
CAPABILITIES = REGISTRY['capabilities']


def infer(text):
    scores = {key: (0.9 if re.search(c['patterns'], text, re.I) else 0.08)
              for key, c in CAPABILITIES.items()}
    if not any(scores[k] > .5 for k in ('analyze', 'write', 'plan')):
        scores['answer'] = .85
    return scores


def compose(text, dataset=None, scores=None, selected=None):
    local = infer(text)
    # KEV can reject a keyword match (e.g. "不要图表，只写文字").
    merged = {k: float(scores[k]) if scores and k in scores else local[k] for k in CAPABILITIES}
    chosen = set(selected if selected is not None else [k for k, p in merged.items() if p >= .58])
    chosen &= CAPABILITIES.keys()
    if chosen - {'answer'}:
        chosen.discard('answer')
    if not chosen:
        chosen.add('answer')
    steps = []
    for key in CAPABILITIES:
        if key not in chosen:
            continue
        deps = []
        if key in ('write', 'plan') and 'analyze' in chosen:
            deps.append('analyze')
        if key == 'plan' and 'write' in chosen:
            deps.append('write')
        steps.append({'id': key, 'label': CAPABILITIES[key]['label'],
                      'depends': deps, 'cost': CAPABILITIES[key]['cost'],
                      'blocked': key == 'analyze' and not dataset})
    return {'steps': steps, 'scores': merged, 'components': select_components(chosen),
            'mode': 'mixed' if len(steps) > 1 else steps[0]['id'],
            'needs_data': any(s['blocked'] for s in steps),
            'cloud': any(s['cost'] == 'cloud' for s in steps)}


def select_components(capabilities, previous=(), budget=7):
    candidates = [(key, c) for key, c in REGISTRY['components'].items()
                  if c['capability'] in capabilities or (key == 'document' and 'answer' in capabilities)]
    best, best_score = [], -1
    for mask in range(1 << len(candidates)):
        chosen = [(key, c) for i, (key, c) in enumerate(candidates) if mask & (1 << i)]
        if sum(c['previewCost'] for _, c in chosen) > budget:
            continue
        score = len({c['capability'] for _, c in chosen}) * 3 + sum(c['weight'] + (.12 if key in previous else 0) for key, c in chosen)
        if score > best_score:
            best, best_score = [key for key, _ in chosen], score
    return best


def parse_dataset(raw, name='粘贴的数据', demo=False):
    """Parse a bounded rectangular CSV/TSV with at least one fully numeric column."""
    if not isinstance(raw, str) or len(raw) > 100000:
        raise ValueError('数据需为不超过 100 KB 的 CSV 或 TSV 文本')
    raw = raw.strip().lstrip('\ufeff')
    dialect = '\t' if '\t' in raw.split('\n')[0] else ','
    rows = list(csv.reader(io.StringIO(raw), delimiter=dialect))
    if len(rows) < 3 or len(rows) > 501:
        raise ValueError('请提供表头和 2–500 行数据')
    headers = [s.strip() for s in rows[0]]
    if not 2 <= len(headers) <= 16 or not all(headers) or len(set(headers)) != len(headers):
        raise ValueError('表头需要 2–16 个不重复的列名')
    body = [[s.strip() for s in row] for row in rows[1:] if any(s.strip() for s in row)]
    if len(body) < 2 or any(len(r) != len(headers) for r in body):
        raise ValueError('每行列数需一致，并至少有两行数据')
    numeric = []
    for i in range(len(headers)):
        try:
            vals = [float(row[i]) for row in body]
            if all(math.isfinite(v) and abs(v) < 1e15 for v in vals):
                numeric.append(i)
        except ValueError:
            pass
    if not numeric:
        raise ValueError('需要至少一列完整的有限数值')
    return {'name': str(name)[:100], 'headers': headers, 'rows': body,
            'numeric': numeric, 'demo': bool(demo)}


def analyze(dataset):
    columns = []
    for index in dataset['numeric']:
        vals = [float(r[index]) for r in dataset['rows']]
        columns.append({'name': dataset['headers'][index], 'index': index,
                        'total': sum(vals), 'mean': sum(vals) / len(vals),
                        'min': min(vals), 'max': max(vals), 'first': vals[0], 'last': vals[-1],
                        'change': ((vals[-1] - vals[0]) / abs(vals[0]) * 100) if vals[0] else None,
                        'values': vals})
    label_index = next((i for i in range(len(dataset['headers'])) if i not in dataset['numeric']), None)
    return {'dataset': dataset, 'columns': columns, 'count': len(dataset['rows']),
            'labels': [r[label_index] if label_index is not None else str(i + 1)
                       for i, r in enumerate(dataset['rows'])]}
