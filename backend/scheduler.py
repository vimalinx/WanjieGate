"""Bounded, durable, idempotent execution of typed capability graphs."""
import hashlib
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from .composition import analyze, compose
from .providers import ProviderError
from .store import ident

TERMINAL = {'complete', 'failed', 'cancelled', 'interrupted'}


class Scheduler:
    def __init__(self, store, generator):
        self.store, self.generator = store, generator
        self.lock = threading.RLock()
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='wanjie')
        for job in store.jobs():
            if job['status'] not in TERMINAL:
                job['status'] = 'interrupted'
                job['error'] = '服务重启，执行已中断；已完成内容保留，上游调用没有自动重放。'
                self.event(job, 'interrupted', job['error'])

    def event(self, job, status, text, **extra):
        job['events'].append({'seq': len(job['events']) + 1, 'status': status,
                              'text': text, 'time': time.time(), **extra})
        job['updated'] = time.time()
        self.store.save_job(job)

    def submit(self, workspace, text, selected, request_id, local_only=False):
        fingerprint = hashlib.sha256(json.dumps([workspace, text, selected, local_only], sort_keys=True).encode()).hexdigest()
        with self.lock:
            prior = self.store.job(request_id=request_id)
            if prior:
                if prior['fingerprint'] != fingerprint:
                    raise ValueError('发送编号已用于不同内容')
                return prior
            active = [j for j in self.store.jobs() if j['status'] not in TERMINAL]
            if any(j['workspace'] == workspace for j in active):
                raise ValueError('这个空间还有任务在进行，请先等待或停止')
            if len(active) >= 6:
                raise ValueError('执行队列已满，请稍后发送')
            w = self.store.workspace(workspace)
            plan = compose(text, w['dataset'], selected=selected)
            if plan['needs_data']:
                raise ValueError('分析需要数据。请先粘贴 CSV，或取消“分析数据”')
            if local_only and plan['cloud']:
                raise ValueError('仅本地模式不调用生成模型。可使用数据分析或保存笔记')
            job = {'id': ident(), 'workspace': workspace, 'request_id': request_id,
                   'fingerprint': fingerprint, 'text': text, 'plan': plan, 'status': 'queued',
                   'created': time.time(), 'events': [], 'cancel_requested': False, 'artifacts': []}
            def record(ws):
                if not ws['messages']:
                    ws['title'] = text.replace('\n', ' ')[:32]
                ws['messages'].append({'id': ident(), 'text': text, 'job': job['id'], 'created': time.time()})
            self.store.mutate(workspace, record)
            self.event(job, 'queued', '已进入执行队列')
            self.pool.submit(self.run, job['id'], w)
            return job

    def cancel(self, key):
        with self.lock:
            job = self.store.job(key)
            if not job:
                raise KeyError('执行不存在')
            if job['status'] not in TERMINAL:
                job['cancel_requested'] = True
                # queued jobs have made no calls; active calls may already be upstream.
                if job['status'] == 'queued':
                    job['status'] = 'cancelled'
                self.event(job, 'cancelling', '已请求停止；已发出的模型请求可能仍在完成，结果不会继续写入')
            return job

    def run(self, key, snapshot):
        context = {'dataset': snapshot['dataset'], 'recent_artifacts': snapshot['artifacts'][-4:]}
        try:
            for step in self.store.job(key)['plan']['steps']:
                with self.lock:
                    job = self.store.job(key)
                    if job['cancel_requested'] or job['status'] == 'cancelled':
                        job['status'] = 'cancelled'
                        self.event(job, 'cancelled', '已停止，已完成内容保留')
                        return
                    job['status'] = 'running'
                    job['current'] = step['id']
                    self.event(job, 'running', step['label'], step=step['id'])
                artifact = self.execute(step['id'], job, context)
                with self.lock:
                    job = self.store.job(key)
                    if job['cancel_requested']:
                        job['status'] = 'cancelled'
                        self.event(job, 'cancelled', '已停止，当前请求结果未写入')
                        return
                    artifact['job'] = key
                    artifact['components'] = job['plan']['components']
                    artifact = self.store.put_artifact(job['workspace'], artifact)
                    job['artifacts'].append(artifact['id'])
                    context[step['id']] = artifact['data']
                    self.event(job, 'step-complete', step['label'] + '已完成', artifact=artifact['id'])
            with self.lock:
                job = self.store.job(key)
                job['status'] = 'complete'
                self.event(job, 'complete', '已完成，内容已保存')
        except Exception as exc:
            with self.lock:
                job = self.store.job(key)
                job['status'] = 'cancelled' if job['cancel_requested'] else 'failed'
                job['error'] = str(exc) if isinstance(exc, (ProviderError, ValueError)) else '执行失败，已完成内容保留。请检查服务日志。'
                self.event(job, job['status'], job['error'])

    def execute(self, step, job, context):
        if step == 'analyze':
            return {'type': 'analysis', 'title': context['dataset']['name'],
                    'data': analyze(context['dataset']), 'source': '本地计算'}
        # The context is a snapshot. A new run appends rather than overwrites user edits.
        compact = {'current_step': step, 'current_request': job['text'], 'previous_content': context['recent_artifacts']}
        if context.get('analyze'):
            a = context['analyze']
            compact['statistics'] = {'count': a['count'], 'columns': a['columns'],
                                     'demo': a['dataset']['demo'], 'name': a['dataset']['name'],
                                     'definitions': 'change 为本组最后一条相对第一条的变化，不是环比或同比；没有前期数据。不得编造变化原因。'}
        elif context.get('dataset'):
            compact['dataset'] = context['dataset']
        if context.get('write'):
            compact['current_document'] = context['write']
        prompt = json.dumps(compact, ensure_ascii=False)
        if len(prompt) > 28000:
            raise ValueError('关联内容超过本次生成长度，请在新空间选取需要的资料')
        count_match = re.search(r'(1[0-2]|[1-9])\s*(?:条|个|项)[^，。；\n]{0,12}(?:任务|行动|计划|步骤)', job['text'])
        requested_count = int(count_match.group(1)) if count_match else None
        purpose = {'write': '当前步骤：形成一篇精炼的可编辑文稿，使用 Markdown。不要额外生成任务清单。',
                   'answer': '当前步骤：回答用户的问题，使用简洁的中文 Markdown。',
                   'plan': '当前步骤：只输出一个 JSON 数组，含 3–7 个具体行动项，每项形如 {"title":"行动","detail":"完成标准"}，不含 Markdown 围栏，不编造截止日期或负责人。'}[step]
        if step == 'plan' and requested_count:
            purpose += f' 用户明确要求 {requested_count} 条，只输出 {requested_count} 项。'
        text, meta = self.generator.generate(prompt, purpose, job['id'] + '-' + step)
        if step == 'plan':
            raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
            try:
                items = json.loads(raw)
                if not isinstance(items, list) or not 1 <= len(items) <= 12:
                    raise ValueError()
                if any(not isinstance(t, dict) or not isinstance(t.get('title'), str) or not t['title'].strip()
                       or not isinstance(t.get('detail', ''), str) for t in items):
                    raise ValueError()
            except (ValueError, TypeError):
                raise ProviderError('模型返回的任务格式无效。原始响应已保留，没有自动重试。')
            if requested_count:
                items = items[:requested_count]
            return {'type': 'tasks', 'title': '接下来，可以这样做', 'source': self.generator.model,
                    'data': {'items': [{'id': ident(), 'title': t['title'][:200], 'detail': t.get('detail', '')[:800], 'done': False} for t in items]}, 'receipt': meta}
        return {'type': 'document', 'title': '文稿' if step == 'write' else '一起想想',
                'data': {'text': text}, 'source': self.generator.model, 'receipt': meta}
