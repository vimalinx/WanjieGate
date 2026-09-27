"""Public reference lookup. Excerpts come from source pages, never model prose."""
import json
import re
import urllib.parse
import urllib.request
from .semantic import NoRedirect
from .protocol import Fault, now

def search(query):
    language='zh' if re.search(r'[\u3400-\u9fff]',query) else 'en'
    params={'action':'query','format':'json','formatversion':'2','generator':'search','gsrsearch':query,
            'gsrnamespace':'0','gsrlimit':'4','prop':'extracts|info|pageimages','inprop':'url',
            'exintro':'1','explaintext':'1','exsentences':'3','exlimit':'4','piprop':'thumbnail','pithumbsize':'640'}
    # Fixed provider host only; honor the user's configured HTTPS proxy.
    url='https://'+language+'.wikipedia.org/w/api.php?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={'User-Agent':'WanjieGate/0.2 (public-reference-reader)','Accept':'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=12) as response:raw=response.read(1000001)
    if len(raw)>1000000:raise Fault('response_too_large','参考来源响应超过限制')
    payload=json.loads(raw)
    if payload.get('error'):raise Fault('reference_unavailable','参考来源返回错误，未生成替代引用')
    entries=[]
    for page in sorted(payload.get('query',{}).get('pages',[]),key=lambda x:x.get('index',0)):
        url=page.get('fullurl','');text=page.get('extract','').strip()
        if not url.startswith('https://'+language+'.wikipedia.org/') or not text:continue
        image=page.get('thumbnail',{}).get('source','')
        if not image.startswith('https://upload.wikimedia.org/'):image=''
        entries.append({'id':str(page['pageid']),'title':page['title'],'text':text[:1200],
                        'url':url,'image':image,'source':'Wikipedia','retrievedAt':now()})
    return {'query':query,'entries':entries,'source':'Wikipedia · 原文摘录','retrievedAt':now()}


def web_search(query,receipt_root):
    import hashlib
    import html
    import os
    import subprocess
    import time
    from pathlib import Path
    from ..providers import ProviderError
    from .protocol import uid
    folder=Path(receipt_root)/uid();folder.mkdir(parents=True,mode=0o700)
    def save(name,text):
        with os.fdopen(os.open(folder/name,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as f:f.write(text)
    save('request.json',json.dumps({'query':query,'count':4},ensure_ascii=False))
    started=time.monotonic();code=-1
    with os.fdopen(os.open(folder/'response.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as out,os.fdopen(os.open(folder/'stderr',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as err:
        try:code=subprocess.run(['lr','exec','agentkey','search','@'+str(folder/'request.json')],stdout=out,stderr=err,timeout=45,check=False).returncode
        except (subprocess.TimeoutExpired,OSError):pass
    save('meta.json',json.dumps({'pack':'agentkey','operation':'search','exitCode':code,'latencyMs':round((time.monotonic()-started)*1000)}))
    if code!=0:raise ProviderError('网页检索未完成；已保存回执，不自动重试或替换来源。')
    try:
        payload=json.loads((folder/'response.json').read_text());results=payload['data']['web']['results']
        if not isinstance(results,list):raise ValueError()
    except (ValueError,KeyError,TypeError):raise ProviderError('网页检索响应格式异常；原始回执已保留。') from None
    entries=[]
    for row in results[:4]:
        url=row.get('url','');parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:continue
        text=html.unescape(re.sub(r'<[^>]*>','',row.get('description','')))
        if not text:continue
        entries.append({'id':hashlib.sha256(url.encode()).hexdigest()[:16],'title':html.unescape(row.get('title',parsed.hostname)),
                        'text':text[:1200],'url':url,'image':'','source':parsed.hostname,'kind':'search-snippet','retrievedAt':now()})
    return {'query':query,'entries':entries,'source':'网页搜索 · 摘要','retrievedAt':now(),'receipt':folder.name,'creditsCharged':payload.get('credits_charged')}
