"""Trusted built-ins. Each provider has typed input, effects, and an explicit module.

Generated text is data, never executable code. Filesystem providers are confined to
this registered project, reject symlinks/secret stores, and do not invoke a shell.
"""
import hashlib
import json
import re
import subprocess
import urllib.request
from pathlib import Path
from .protocol import Fault, now, uid
from .context import accessible
from .policies import POLICIES
from .control import contract as control_contract
from ..composition import parse_dataset, analyze
from ..live_runtime import parse_scene, SCENE_PROMPT
from ..market import Market

PROJECT=Path(__file__).resolve().parents[2]
DENIED={'.git','.data','.ai','.venv','vendor','node_modules','__pycache__'}

def obj(properties,required=()):return {'type':'object','properties':properties,'required':list(required),'additionalProperties':False}
def string(n=12000):return {'type':'string','maxLength':n}
def artifact(kind,title,content,source):return {'kind':kind,'title':title,'content':content,'source':source}

def project_file(name,write=False):
    path=Path(name)
    if path.is_absolute() or '..' in path.parts or any(p in DENIED or p.startswith('.env') for p in path.parts):
        raise Fault('scope_denied','路径必须位于本项目可访问文件中')
    target=(PROJECT/path).resolve()
    if not target.is_relative_to(PROJECT) or any((PROJECT/Path(*path.parts[:i])).is_symlink() for i in range(1,len(path.parts)+1)):
        raise Fault('scope_denied','不允许通过符号链接访问')
    if write and (not path.parts or path.parts[0] not in ('static','backend','docs','ideas','tools','protocol')):
        raise Fault('scope_denied','此目录不能通过编辑能力修改')
    if not target.is_file() or target.stat().st_size>1_000_000:raise Fault('invalid_file','文件不存在或超过 1 MB')
    return target

class Semantic:
    def __init__(self,url=None):
        import os
        self.url=url or os.environ.get('WANJIE_KEV_URL','http://127.0.0.1:8208')
    def observe(self,text,context):
        questions={
            'researching':'Is the user currently researching or looking up information?',
            'implementation':'Is the user currently implementing or debugging software?',
            'writing':'Is the user currently writing or editing a document?',
            'planning':'Is the user currently planning concrete actions?',
            'new_thread':'Does this input clearly start an unrelated new goal instead of continuing the current goal?',
            'resume':'Does the user explicitly want to resume this goal?'}
        body={'model':'kev-latest','state':{'request':text,'intent':context['intentState'],'artifacts':[{'id':a['artifact'],'title':a['title']} for a in context['items']]},
              'questions':{k:{'type':'noul','instructions':v} for k,v in questions.items()}}
        choices={'market.query':'Does the user want current stock prices or market charts?',
                 'text.generate':'Does the user want a written answer, draft or plan?',
                 'repo.search':'Does the user want to search the current source repository?',
                 'memory.retrieve':'Does the user want to find a previously saved fact or note?',
                 'data.analyze':'Does the user want numeric statistics of the imported data?'}
        for i,cue in enumerate(choices.values()):body['questions']['cap_'+str(i)]={'type':'noul','instructions':cue}
        for i,a in enumerate(context['items'][:12]):body['questions']['artifact_'+str(i)]={'type':'noul','instructions':'Is artifact '+a['artifact']+' relevant to the current request?'}
        notifications=context.get('notifications',[])[:8]
        body['state']['notifications']=notifications
        body['questions']['interruptible']={'type':'noul','instructions':'Is the user currently interruptible, rather than concentrating on a foreground task?'}
        for i,n in enumerate(notifications):body['questions']['notification_'+str(i)]={'type':'noul','instructions':'Is notification '+n['id']+' relevant to the current intent?'}
        request=urllib.request.Request(self.url+'/v1/systemone',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=8) as response:data=json.load(response)
            scores={k:float(data['answers'][k]['noul']) for k in body['questions']}
            if not all(0<=v<=1 for v in scores.values()):raise ValueError('invalid score')
        except Exception as exc:raise Fault('semantic_unavailable','语义服务暂不可用，可以继续使用本地内容与手动能力。') from exc
        phase=max(('researching','implementation','writing','planning'),key=lambda k:scores[k])
        signals=[{'name':'intent.phase','value':phase,'score':scores[phase],'model':'kev-latest'},
                 {'name':'intent.continuity','value':'new' if scores['new_thread']>=.5 else 'same','score':scores['new_thread'] if scores['new_thread']>=.5 else 1-scores['new_thread'],'model':'kev-latest'},
                 {'name':'intent.resume','value':True,'score':scores['resume'],'model':'kev-latest'}]
        signals.extend({'name':'artifact.relevance','value':{'artifact':a['artifact'],'relevant':scores['artifact_'+str(i)]>=.5},'score':max(scores['artifact_'+str(i)],1-scores['artifact_'+str(i)]),'model':'kev-latest'} for i,a in enumerate(context['items'][:12]))
        signals.extend({'name':'notification.relevance','value':{'notification':n['id'],'relevant':scores['notification_'+str(i)]>=.5,'interruptible':scores['interruptible']>=.8},'score':max(scores['notification_'+str(i)],1-scores['notification_'+str(i)]),'model':'kev-latest'} for i,n in enumerate(notifications))
        ranked=sorted([{'capability':cap,'score':scores['cap_'+str(i)]} for i,cap in enumerate(choices)],key=lambda item:item['score'],reverse=True)
        signals.append({'name':'capability.selection','value':ranked,'score':ranked[0]['score'],'model':'kev-latest'})
        return {'signals':signals,'artifacts':[]}

def install(kernel,generator=None,market=None,semantic=None):
    market=market or Market()
    if semantic is None:
        import os
        provider=os.environ.get('WANJIE_SEMANTIC_PROVIDER','openrouter')
        if provider=='openrouter':
            from .semantic import OpenRouterSemantic
            semantic=OpenRouterSemantic(kernel.store.path.parent/'receipts'/'semantic')
        elif provider=='kev':semantic=Semantic()
        else:raise Fault('invalid_provider','未知语义提供者')
    output={'type':'object','properties':{'artifacts':{'type':'array','maxItems':30,'items':obj({'kind':string(80),'title':string(200),'content':{},'source':string(300)},['kind','title','content','source'])}},'required':['artifacts']}
    def register(id_,title,inputs,handler,effect='L0',permissions=(),network=False,cost='none',kind='capability'):
        module='builtin.'+id_
        spec={'id':id_,'title':title,'module':module,'inputSchema':inputs,'outputSchema':output,'sideEffect':effect,
              'permissions':list(permissions),'network':network,'cost':cost,'reversible':effect!='L3'}
        manifest={'id':module,'version':'0.1.0','protocolVersion':'0.1','kind':kind,'title':title,'provides':[id_],
                  'accepts':['command.capability.run'],'emits':['result.capability.result','event.artifact.created'],
                  'requires_context':['intent'],'permissions':list(permissions),'side_effect':effect,'network':network,
                  'cost':cost,'reversible':effect!='L3','latency':'variable' if network else 'low','trusted':True}
        kernel.register(spec,manifest,handler)

    def get_artifact(task,id_,kind=None):
        with kernel.db.transaction() as tx:
            values=accessible(tx,task['intent'])
            if id_ not in values:raise Fault('scope_denied','内容不在当前工作集范围')
            a=values[id_]
            if kind and a['kind']!=kind:raise Fault('wrong_artifact_type','内容类型不匹配')
            return a

    def import_data(t,progress,cancel):
        data=parse_dataset(t['input']['text'],t['input'].get('name','导入数据'))
        return {'artifacts':[artifact('dataset',data['name'],data,'本地导入')]}
    register('data.import','导入表格',obj({'text':string(100000),'name':string(100)},['text']),import_data)
    def analyze_data(t,progress,cancel):
        data=get_artifact(t,t['input']['artifact'],'dataset')['content']
        result=analyze(data)
        return {'artifacts':[artifact('analysis',data['name']+' · 统计',result,'本地计算')]}
    register('data.analyze','分析数据',obj({'artifact':string(160)},['artifact']),analyze_data)

    def generate(t,progress,cancel):
        if generator is None:raise Fault('provider_unavailable','生成提供者未配置')
        mode=t['input'].get('mode','answer')
        purpose={'answer':'回答问题，使用中文 Markdown。','write':'形成可编辑文稿，使用中文 Markdown。',
                 'plan':'仅输出 JSON 数组，每项为 {"title":"行动","detail":"完成标准"}，含3到7项。', 'scene':SCENE_PROMPT}[mode]
        raw,meta=generator.generate(json.dumps({'request':t['input']['text'],'context':t['context']},ensure_ascii=False),purpose,t['id']+'-'+uid())
        if cancel():raise Fault('cancelled','任务已停止')
        if mode=='scene':content=parse_scene(raw);kind='scene';title=content['title']
        elif mode=='plan':
            items=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip()))
            if not isinstance(items,list) or not 1<=len(items)<=20 or any(not isinstance(x,dict) or not isinstance(x.get('title'),str) or not x['title'].strip() for x in items):raise Fault('invalid_output','行动格式无效')
            content={'items':[{'id':uid(),'title':x['title'][:200],'detail':str(x.get('detail',''))[:1000],'done':False} for x in items]};kind='tasks';title='行动清单'
        else:kind='document';content={'text':raw};title='文稿' if mode=='write' else '回答'
        return {'artifacts':[artifact(kind,title,content,meta.get('model',generator.model))],'receipt':meta}
    register('text.generate','生成内容',obj({'text':string(),'mode':{'enum':['answer','write','plan','scene']}},['text']),generate,permissions=['model.invoke'],network=True,cost='metered')
    register('market.query','查询行情',obj({'text':string(1000)},['text']),lambda t,p,c:{'artifacts':[artifact('scene','行情',market.scene(t['input']['text']),'公开行情；以来源时间为准')]},permissions=['network.market'],network=True)
    def web_read(t,p,c):
        from .web import read
        content=read(t['input']['url'])
        return {'artifacts':[artifact('web',content['title'][:200],content,content['url'][:300])]}
    register('web.read','读取公开网页',obj({'url':string(2000)},['url']),web_read,permissions=['network.web'],network=True)

    def reference_search(t,p,c):
        from .references import search,web_search
        content=search(t['input']['query']) if t['input'].get('source')=='wikipedia' else web_search(t['input']['query'],kernel.store.path.parent/'receipts'/'references')
        return {'artifacts':[artifact('references','相关资料 · '+t['input']['query'][:60],content,content['source'])]}
    register('reference.search','查找公开参考资料',obj({'query':string(160),'source':{'enum':['web','wikipedia']}},['query']),reference_search,permissions=['network.references'],network=True,cost='metered')

    def semantic_observe(t,p,c):
        ctx={**t['context'],'event':t['input'].get('event'),'view':t['input'].get('view',{}),'intentState':kernel.db.get(t['intent'],'intent')['state'],
             'notifications':[{'id':n['id'],'title':n['title'],'text':n['text']} for n in kernel.db.list('notification',t['intent']) if n['status']!='read']}
        with kernel.db.transaction() as tx:
            ctx['intentCandidates']=[{'id':i['id'],'title':i['title'],'goal':i['state'].get('goal','')} for i in sorted(tx.list('intent'),key=lambda i:(i['id']!=t['intent'],-i['updated']))[:8]]
            members={m['artifact']:m for m in tx.list('member',t['intent'])}
            ctx['targetCandidates']=[{'artifact':a['id'],'title':a['title'],'kind':a['kind'],'tier':members.get(a['id'],{}).get('tier','WARM')} for a in accessible(tx,t['intent']).values()]
        ctx['selectedArtifact']=(ctx.get('event') or {}).get('selectedArtifact','')
        return semantic.observe(t['input']['text'],ctx)
    register('semantic.observe','JEV 语义判断' if getattr(semantic,'network',False) else '语义判断',obj({'text':string(),'event':control_contract('raw-event'),'view':json.loads((Path(__file__).resolve().parents[2]/'protocol/extensions/v0.1/view-context.schema.json').read_text())},['text']),semantic_observe,kind='operator',network=getattr(semantic,'network',False),cost=getattr(semantic,'cost','none'),permissions=['model.semantic'] if getattr(semantic,'network',False) else [])

    def retrieve(t,p,c):
        query=t['input']['query'].casefold();tokens=[x for x in re.split(r'\s+',query) if x]
        with kernel.db.transaction() as tx:items=list(accessible(tx,t['intent']).values())
        ranked=[]
        for a in items:
            if a['kind'] not in ('memory','note','document'):continue
            hay=(a['title']+' '+json.dumps(a['content'],ensure_ascii=False)).casefold()
            score=sum(hay.count(token) for token in tokens)
            if score:ranked.append((score,a))
        ranked.sort(key=lambda x:x[0],reverse=True)
        content={'query':query,'matches':[{'artifact':a['id'],'title':a['title'],'score':score,'source':a['source']} for score,a in ranked[:20]],'method':'literal-search'}
        return {'artifacts':[artifact('search-results','记忆检索',content,'本地文字检索')],'matches':content['matches']}
    register('memory.retrieve','检索记忆',obj({'query':string(1000)},['query']),retrieve)

    def repo_search(t,p,c):
        query=t['input']['query'];matches=[]
        if not query:raise Fault('empty_query','请输入检索文字')
        for folder in ('backend','static','docs','ideas','protocol','tools'):
            for path in (PROJECT/folder).rglob('*'):
                if c():raise Fault('cancelled','任务已停止')
                if path.is_symlink() or not path.is_file() or any(x in DENIED for x in path.relative_to(PROJECT).parts) or path.stat().st_size>500000:continue
                try:lines=path.read_text().splitlines()
                except UnicodeError:continue
                for n,line in enumerate(lines,1):
                    if query.casefold() in line.casefold():matches.append({'path':str(path.relative_to(PROJECT)),'line':n,'text':line[:500]})
                    if len(matches)>=100:break
                if len(matches)>=100:break
            if len(matches)>=100:break
        return {'artifacts':[artifact('search-results','仓库搜索',{'query':query,'matches':matches},'WanjieGate 本地仓库')]}
    register('repo.search','搜索本项目',obj({'query':string(500)},['query']),repo_search,permissions=['filesystem.read'])
    def repo_read(t,p,c):
        path=project_file(t['input']['path']);content=path.read_text()
        return {'artifacts':[artifact('code',t['input']['path'],{'path':t['input']['path'],'text':content,'sha256':hashlib.sha256(content.encode()).hexdigest()},'WanjieGate 本地文件')]}
    register('repo.read','读取本项目文件',obj({'path':string(1000)},['path']),repo_read,permissions=['filesystem.read'])
    def patch(t,p,c):
        inp=t['input'];path=project_file(inp['path'],True);old=path.read_text()
        if hashlib.sha256(old.encode()).hexdigest()!=inp['sha256']:raise Fault('revision_conflict','文件已经变化，请重新读取')
        if c():raise Fault('cancelled','任务已停止')
        # Store the original before writing. No shell, no generated code execution.
        p({'text':'已保留原文件内容','artifact':artifact('code',inp['path']+' · 修改前',{'path':inp['path'],'text':old,'sha256':inp['sha256']},'编辑前快照')})
        path.write_text(inp['text'])
        return {'artifacts':[artifact('code',inp['path'],{'path':inp['path'],'text':inp['text'],'sha256':hashlib.sha256(inp['text'].encode()).hexdigest()},'用户授权编辑')]}
    register('patch.apply','修改本项目文件',obj({'path':string(1000),'sha256':string(64),'text':string(100000)},['path','sha256','text']),patch,effect='L2',permissions=['filesystem.write'])

    def process(args,title,t,c):
        import os
        import signal
        import tempfile
        import time
        with tempfile.TemporaryFile() as capture:
            proc=subprocess.Popen(args,cwd=PROJECT,stdout=capture,stderr=subprocess.STDOUT,start_new_session=True)
            started=time.monotonic()
            def stop():
                try:os.killpg(proc.pid,signal.SIGTERM)
                except ProcessLookupError:return
                try:proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try:os.killpg(proc.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    proc.wait()
            try:
                while proc.poll() is None:
                    if c() or time.monotonic()-started>60 or os.fstat(capture.fileno()).st_size>1000000:
                        stop()
                        raise Fault('cancelled' if c() else 'resource_limit','进程已停止：取消、超时或输出超过限制')
                    time.sleep(.03)
                length=capture.seek(0,2);capture.seek(max(0,length-60000));out=capture.read(60000)
                content={'text':out.decode(errors='replace'),'exitCode':proc.returncode,'command':args}
                return {'artifacts':[artifact('terminal',title,content,'本机进程')],'exitCode':proc.returncode}
            finally:
                if proc.poll() is None:stop()
    register('git.diff','查看代码差异',obj({}),lambda t,p,c:process(['git','diff','--no-ext-diff','--no-textconv'],'代码差异',t,c),permissions=['filesystem.read'])
    register('test.run','运行项目测试',obj({}),lambda t,p,c:process(['python3','tools/selftest.py'],'项目测试',t,c),effect='L2',permissions=['process.test'])
    def run_code(t,p,c):
        import shutil
        if not shutil.which('bwrap') or not shutil.which('prlimit'):
            raise Fault('sandbox_unavailable','代码执行需要 bubblewrap 与 prlimit；不会降级为宿主执行')
        args=['prlimit','--as=268435456','--cpu=10','--fsize=1048576','--nofile=64','--',
              'bwrap','--unshare-all','--die-with-parent','--new-session','--clearenv',
              '--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib','/lib64',
              '--symlink','usr/bin','/bin','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--chdir','/tmp',
              '--setenv','PATH','/usr/bin','--setenv','PYTHONDONTWRITEBYTECODE','1','python3','-I','-c',t['input']['code']]
        return process(args,'隔离 Python 执行',t,c)
    register('code.run','隔离执行 Python',obj({'code':string(12000)},['code']),run_code,effect='L2',permissions=['process.sandbox'])

    def workflow(t,progress,cancel):
        steps=t['input']['steps'];done={};known=set()
        if not steps:raise Fault('empty_workflow','组合至少需要一个步骤')
        # Validate complete graph and permissions before the first operation.
        with kernel.db.transaction() as tx:
            for step in steps:
                if step['id'] in known or any(d not in known for d in step.get('dependsOn',[])):raise Fault('invalid_graph','步骤必须唯一并按依赖顺序排列')
                known.add(step['id']);cap=step['capability']
                if cap in ('workflow.run','agent.run','semantic.observe') or cap not in kernel.providers:raise Fault('invalid_graph','此能力不能嵌入组合')
                spec=kernel.providers[cap]['spec']
                kernel._permission(tx,spec,t['intent'],step['input'],None,'human')
        for step in steps:
            if cancel():raise Fault('cancelled','组合已停止')
            cap=step['capability'];spec=kernel.providers[cap]['spec']
            inp=dict(step['input'])
            for field,dependency in step.get('bindings',{}).items():
                if dependency not in step.get('dependsOn',[]) or dependency not in done or not done[dependency]:raise Fault('invalid_binding','依赖产物不存在')
                inp[field]=done[dependency][0]
            from .protocol import validate
            validate(inp,spec['inputSchema'])
            with kernel.db.transaction() as tx:
                if not tx.get(spec['module'],'module')['enabled']:raise Fault('module_disabled','步骤模块已停用')
                kernel._permission(tx,spec,t['intent'],inp,None,'human',consume=True)
                from .context import build
                ctx=build(tx,t['intent'])
                tx.emit('workflow.step.started',{'task':t['id'],'step':step['id'],'capability':cap},t['intent'],t['command'])
            result=kernel.providers[cap]['handler']({**t,'input':inp,'context':ctx},progress,cancel)
            validate(result,spec['outputSchema'])
            before=kernel.db.get(t['id'],'task')['artifacts']
            for a in result['artifacts']:progress({'text':step['id']+' 完成','artifact':a})
            done[step['id']]=[x for x in kernel.db.get(t['id'],'task')['artifacts'] if x not in before]
            if result.get('exitCode',0)!=0:raise Fault('process_failed','步骤 '+step['id']+' 返回非零退出码，输出已保留')
        return {'artifacts':[],'steps':done}
    step=obj({'id':string(80),'capability':string(160),'input':{'type':'object'},'dependsOn':{'type':'array','items':string(80),'maxItems':12},'bindings':{'type':'object','additionalProperties':string(80)}},['id','capability','input'])
    graph=obj({'steps':{'type':'array','items':step,'minItems':1,'maxItems':12}},['steps'])
    register('workflow.run','执行能力组合',graph,workflow)
    register('agent.run','临时工作者',graph,workflow)
    def passive(id_,kind,title,provides,accepts,emits):
        kernel.register_module({'id':id_,'version':'0.1.0','protocolVersion':'0.1','kind':kind,'title':title,
            'provides':provides,'accepts':accepts,'emits':emits,'requires_context':['intent'],'permissions':[],
            'side_effect':'L0','network':False,'cost':'none','reversible':True,'latency':'low','trusted':True})
    passive('builtin.policy','policy','语义策略',[p['id'] for p in POLICIES],
            ['signal.intent.phase','signal.intent.continuity','signal.artifact.relevance','signal.notification.relevance','signal.intent.resume','signal.capability.selection'],
            ['command.intent.update','command.intent.warm','command.context.set','command.notification.resolve'])
    for primitive in ('Text','Code','Terminal','Web','Media','Canvas','Timeline','Table','Conversation','Inspector'):
        passive('builtin.view.'+primitive,'view',primitive+' 视图',['ui.'+primitive],['event.artifact.created','event.artifact.updated','event.intent.updated'],[])
