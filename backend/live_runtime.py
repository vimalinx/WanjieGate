"""Automatic, read-only content runtime. Latest intent owns the visible scene."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import re
import threading
import time
import uuid
from .market import Market

MARKET_PATTERN = r'股票|股价|股市|行情|大盘|美股|港股|A股|上证|深证|恒生|纳斯达克|标普|\b(?:stock|stocks|ticker|NASDAQ|AAPL|TSLA|NVDA)\b'
MARKET_CUE = 'Does the user request stock quotes, stock market conditions, equity price movements or a stock ticker? Not writing fiction about stocks or generic marketing.'
SCENE_PROMPT = '''你负责把用户目的变成已有实际内容的交互界面。只输出一个 JSON 对象，禁止代码围栏。
格式 {"title":"短标题","blocks":[...]}。可用块：
{"type":"text","title":"短标题","text":"直接回答或写好的文字，支持Markdown"}
{"type":"tasks","title":"行动","items":["具体可执行的任务"]}
{"type":"table","title":"对比","headers":["列名"],"rows":[["单元格"]]}
{"type":"choices","title":"需要用户补充的问题","items":[{"label":"短选项","value":"选择后继续执行的完整请求"}]}
根据目的自由选择和组合1至4块，总正文不超过700个中文字符。不要复述用户问题，不要空模板，不要把用户原句拆成任务。
缺少影响答案的必要信息时给简短问题与合适选项；可以直接完成的写作或计划就直接给成果。
没有实时数据源的新闻、天气、价格等不得编造当前数值或声称已查询。工具仅提供输入里的数据；不能声称执行了外部动作。股票实时行情由另一条专用接口负责。
'''


def clean_string(value, limit=8000):
    if not isinstance(value, str):
        raise ValueError('界面内容必须是文字')
    return value[:limit]


def parse_scene(raw):
    raw=re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip())
    value=json.loads(raw)
    if not isinstance(value,dict) or not isinstance(value.get('blocks'),list):
        raise ValueError('生成的界面结构无效')
    blocks=[]
    for item in value['blocks'][:6]:
        if not isinstance(item,dict):
            raise ValueError('界面组件无效')
        kind=item.get('type'); block={'type':kind,'title':clean_string(item.get('title',''),120)}
        if kind=='text':
            block['text']=clean_string(item.get('text',''))
            if not block['text'].strip(): continue
        elif kind=='tasks':
            if not isinstance(item.get('items'),list): raise ValueError('行动格式无效')
            block['items']=[clean_string(x,500) for x in item['items'][:20]]
            if not block['items']: continue
        elif kind=='choices':
            if not isinstance(item.get('items'),list): raise ValueError('选项格式无效')
            block['items']=[{'label':clean_string(x['label'],80),'value':clean_string(x['value'],1000)} for x in item['items'][:6] if isinstance(x,dict)]
        elif kind=='table':
            if not isinstance(item.get('headers'),list) or not 1<=len(item['headers'])<=8 or not isinstance(item.get('rows'),list): raise ValueError('表格格式无效')
            block['headers']=[clean_string(x,100) for x in item['headers']]
            block['rows']=[]
            for row in item['rows'][:24]:
                if not isinstance(row,list) or len(row)!=len(block['headers']): raise ValueError('表格列数无效')
                block['rows'].append([clean_string(str(x),500) if isinstance(x,(str,int,float)) else '' for x in row])
        else:
            raise ValueError('生成了不支持的界面组件')
        blocks.append(block)
    if not blocks: raise ValueError('生成的界面没有内容')
    return {'title':clean_string(value.get('title',''),120),'blocks':blocks}


class LiveRuntime:
    def __init__(self, generator, market=None):
        self.generator=generator; self.market=market or Market()
        self.lock=threading.RLock(); self.sessions={}
        self.pool=ThreadPoolExecutor(max_workers=3,thread_name_prefix='live-content')
        self.cache={}

    def observe(self, client, revision):
        if not isinstance(client,str) or not re.fullmatch(r'[a-f0-9-]{32,36}',client) or type(revision) is not int or revision<0:
            raise ValueError('实时会话无效')
        with self.lock:
            now=time.monotonic()
            for key,s in list(self.sessions.items()):
                if not s['running'] and now-s['seen']>1200: del self.sessions[key]
            if client not in self.sessions:
                if len(self.sessions)>=32: raise ValueError('实时会话已满，请稍后再试')
                self.sessions[client]={'revision':revision,'seen':now,'running':False,'pending':None,'fingerprint':None,'result':{'status':'idle','blocks':[]}}
            s=self.sessions[client];s['seen']=now
            if revision>s['revision']:
                s.update(revision=revision,pending=None,fingerprint=None,result={'status':'loading','blocks':[]})
            return revision==s['revision']

    def cancel(self, client, revision):
        self.observe(client,revision)
        with self.lock:
            s=self.sessions[client]
            if s['revision']==revision:
                s.update(pending=None,fingerprint=None,result={'status':'idle','blocks':[]})
        return {'status':'idle'}

    def request(self, client, revision, text, plan, dataset, context, market_score=None, local_only=False):
        if not self.observe(client,revision): return {'status':'superseded','revision':revision,'blocks':[]}
        is_market = market_score>=.55 if market_score is not None else bool(re.search(MARKET_PATTERN,text,re.I))
        route='market' if is_market else 'data' if plan['needs_data'] or (dataset and not plan['cloud']) else 'generate'
        work={'revision':revision,'text':text,'route':route,'context':context,'local_only':local_only}
        fingerprint=json.dumps({**work,'revision':None},sort_keys=True)
        with self.lock:
            s=self.sessions[client]
            if s['revision']!=revision: return {'status':'superseded','blocks':[]}
            if s['fingerprint']==fingerprint: return self.snapshot(client,revision)
            s['fingerprint']=fingerprint
            if route=='data':
                s['result']={'status':'local','route':'data','blocks':[]}
            elif local_only:
                s['result']={'status':'ready','route':route,'title':'仅本地模式','blocks':[{'type':'text','title':'','text':'关闭“仅本地”后会自动获取行情或生成内容。'}]}
            elif len(text.strip())<3:
                s['result']={'status':'ready','route':route,'title':'','blocks':[{'type':'text','title':'','text':'继续描述你想了解或完成的事…'}]}
            else:
                cached=self.cache.get(fingerprint)
                if cached and time.monotonic()-cached[0]<(25 if route=='market' else 300):
                    s['result']={**cached[1],'cached':True}
                else:
                    s['result']={'status':'loading','route':route,'title':'正在获取行情' if route=='market' else '正在生成内容','blocks':[]}
                    s['pending']=(work,fingerprint)
                    if not s['running']:
                        s['running']=True; self.pool.submit(self._drain,client)
            return self.snapshot(client,revision)

    def _drain(self, client):
        while True:
            with self.lock:
                s=self.sessions[client];pending=s['pending'];s['pending']=None
                if not pending:
                    s['running']=False;return
            work,fingerprint=pending
            with self.lock:
                if self.sessions[client]['revision']!=work['revision']:continue
            try:
                if work['route']=='market':result=self.market.scene(work['text'])
                else:
                    prompt=json.dumps({'request':work['text'],'context':work['context']},ensure_ascii=False)
                    raw,meta=self.generator.generate(prompt,SCENE_PROMPT,'live-'+uuid.uuid4().hex)
                    result={**parse_scene(raw),'source':meta.get('model',self.generator.model)}
                result={**result,'status':'ready','route':work['route'],'updated':time.time()}
            except Exception as exc:
                # One attempt. Unknown paid outcomes are not retried automatically.
                message=str(exc) if work['route']=='generate' else '行情源暂不可用，请稍后更新输入。'
                result={'status':'failed','route':work['route'],'title':'这次没有完成','error':message[:240],'blocks':[]}
            with self.lock:
                s=self.sessions[client]
                if s['revision']==work['revision']:
                    s['result']=result
                # Cache failures too: unchanged input must not replay an unknown paid outcome.
                if len(self.cache)>=64:self.cache.pop(next(iter(self.cache)))
                self.cache[fingerprint]=(time.monotonic(),result)

    def snapshot(self, client, revision):
        with self.lock:
            s=self.sessions.get(client)
            if not s or s['revision']!=revision:return {'status':'superseded','blocks':[],'revision':revision}
            return {**deepcopy(s['result']),'revision':revision}

    def shutdown(self):
        with self.lock:
            for s in self.sessions.values():s['pending']=None
        self.pool.shutdown(wait=True)
