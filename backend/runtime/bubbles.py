"""Bubble composition on the existing Intent/Command/Task runtime."""
import copy
import json
import re
from urllib.parse import urlsplit
from .protocol import Fault
from .context import accessible
from ..bubble_catalog import ACTIONS,candidates,merge_options,choose_merge,no_writing

def validate_canvas(content):
    if not isinstance(content,dict):raise Fault('invalid_canvas','画布格式无效')
    bubbles=content.get('bubbles',[]);groups=content.get('groups',[])
    if not isinstance(bubbles,list) or not isinstance(groups,list) or len(bubbles)>100 or len(groups)>50:raise Fault('invalid_canvas','画布对象过多')
    objects={}
    for item in bubbles+groups:
        if not isinstance(item,dict) or not isinstance(item.get('id'),str) or item['id'] in objects:raise Fault('invalid_canvas','对象身份重复或缺失')
        objects[item['id']]=item
    for b in bubbles:
        if b.get('kind') not in ('source','action','link') or not isinstance(b.get('resource'),dict):raise Fault('invalid_canvas','泡泡类型无效')
        r=b['resource']
        if b['kind']=='action' and r.get('action') not in ACTIONS:raise Fault('invalid_action','未知动作')
        if 'url' in r and (not isinstance(r['url'],str) or urlsplit(r['url']).scheme!='https'):raise Fault('invalid_url','仅支持 HTTPS 网页')
        if r.get('detail','full') not in ('full','excerpt','metadata'):raise Fault('invalid_detail','读取范围无效')
    def visit(key,path):
        if key in path or key not in objects:raise Fault('invalid_graph','组合存在循环或缺少成员')
        item=objects[key]
        if 'members' not in item:return [item]
        if item.get('operation') not in ('collect','combine','compare') or not 2<=len(item['members'])<=16:raise Fault('invalid_graph','组合方式无效')
        leaves=[]
        for child in item['members']:leaves+=visit(child,path+[key])
        if len({x['id'] for x in leaves})!=len(leaves):raise Fault('invalid_graph','组合重复使用同一成员')
        steps=sum(x['kind']=='action' or 'url' in x.get('resource',{}) or 'market' in x.get('resource',{}) for x in leaves)+(item['operation']=='compare')
        if steps>4:raise Fault('step_limit','首版组合最多 4 个执行步骤')
        return leaves
    for g in groups:visit(g['id'],[])

def source_text(a,detail):
    c=a['content'];text=c.get('text') if isinstance(c,dict) else c
    if not isinstance(text,str):text=json.dumps(c,ensure_ascii=False)
    if detail=='metadata':raise Fault('source_unread','只有目录信息，请先读取正文')
    return text[:1200] if detail=='excerpt' else text

def freeze_sources(tx,intent,refs,budget):
    allowed=accessible(tx,intent);sources=[]
    for ref in refs:
        a=allowed.get(ref.get('artifact'))
        if a is None:raise Fault('scope_denied','资料不在当前空间')
        if a['version']!=ref.get('version'):raise Fault('revision_conflict','资料版本已变化，请重新选择')
        detail=ref.get('detail','full');text=source_text(a,detail)
        if not text.strip():raise Fault('source_empty','所选资料没有正文')
        sources.append({'id':a['id'],'version':a['version'],'title':a['title'],'source':a['source'],'detail':detail,'text':text})
    if sum(len(s['text']) for s in sources)>budget:raise Fault('source_budget','所选资料超出读取预算，请改用原文片段')
    return sources

def validate_citations(text,sources):
    if any(int(n)<1 or int(n)>len(sources) for n in re.findall(r'\[(\d+)\]',text)):
        raise Fault('citation_invalid','引用校验失败：出现未提供的来源编号')

def flatten(canvas,key):
    objects={i['id']:i for i in canvas['bubbles']+canvas['groups']};item=objects[key]
    if 'members' not in item:return [item]
    result=[]
    for member in item['members']:result+=flatten(canvas,member)
    if item['operation']=='compare':result.append({'id':key+':compare','kind':'action','resource':{'action':'compare'},'title':'对比资料'})
    return result

def prepare_run(tx,intent,payload):
    canvas=tx.get(payload['canvas'],'artifact')
    if canvas['intent']!=intent or canvas['kind']!='bubble-canvas':raise Fault('scope_denied','画布不属于当前空间')
    if canvas['version']!=payload['version']:raise Fault('revision_conflict','画布已变化，请保存后运行')
    content=canvas['content'];validate_canvas(content)
    if payload['groupId'] not in {x['id'] for x in content['groups']}|{x['id'] for x in content['bubbles']}:raise Fault('invalid_graph','组合不存在')
    leaves=flatten(content,payload['groupId']);actions=[x['resource']['action'] for x in leaves if x['kind']=='action']
    if not actions:raise Fault('no_action','这是资料集合，请添加一个动作')
    if any(x['kind']=='link' for x in leaves):raise Fault('unread_link','搜索入口不能作为已读取的资料')
    if no_writing(payload['text']) and 'write' in actions:raise Fault('constraint_conflict','你要求不要代写，请拆开正文生成动作或选择空白文稿')
    if len(actions)>4:raise Fault('step_limit','最多 4 个执行步骤')
    budget=tx.get(intent,'intent')['preferences'].get('contextBudget',12000)
    refs=[x['resource'] for x in leaves if x['kind']=='source' and 'artifact' in x['resource']]
    sources=freeze_sources(tx,intent,refs,budget)
    reads=[copy.deepcopy(x) for x in leaves if x['kind']=='source' and 'artifact' not in x['resource']]
    if len(actions)+len(reads)>4:raise Fault('step_limit','最多 4 个执行步骤（包含资料读取）')
    return {'runId':payload['runId'],'canvas':canvas['id'],'canvasVersion':canvas['version'],'groupId':payload['groupId'],'request':payload['text'],'constraints':{'noWriting':no_writing(payload['text'])},'sources':sources,'reads':reads,'actions':actions,'budget':budget}

def install_bubbles(kernel,jev,generator):
    from .capabilities import obj,string,artifact
    def register(id_,title,inputs,handler):
        module='builtin.'+id_
        spec={'id':id_,'title':title,'module':module,'inputSchema':inputs,'outputSchema':{'type':'object','required':['artifacts'],'properties':{'artifacts':{'type':'array'}}},'sideEffect':'L0','permissions':['network.bubble'],'network':True,'cost':'metered','reversible':True}
        manifest={'id':module,'version':'0.1.0','protocolVersion':'0.1','kind':'capability','title':title,'provides':[id_],'accepts':['command.capability.run'],'emits':['result.capability.result'],'requires_context':['intent'],'permissions':['network.bubble'],'side_effect':'L0','network':True,'cost':'metered','reversible':True,'latency':'variable','trusted':True}
        kernel.register(spec,manifest,handler)
    def suggest(t,p,c):
        inp=t['input'];text=inp['text']
        items=candidates(text,[])  # Saved sources are chosen explicitly, never inferred from generic titles.
        from ..bubble_scenarios import questions,resolve
        decision=jev.decide({'request':text,'candidates':items},questions(items))
        return {'artifacts':[],'decision':decision,**resolve(text,items,decision)}
    def merge(t,p,c):
        inp=t['input'];options=merge_options(inp['left'],inp['right'])
        decision=jev.decide({'request':inp['text'],'left':inp['left'],'right':inp['right']},{'relation':{'type':'choice','instructions':'用户正在把两个泡泡拖到一起。选择最符合目的且可执行的组合含义。遵守否定约束；无法确定则选 none。','criteria':options}})
        return {'artifacts':[],'decision':decision,'merge':choose_merge(decision['answers']['relation'],options)}
    def invoke(t,cap,inp,p,c):
        if c():raise Fault('cancelled','执行已停止')
        spec=kernel.providers[cap]['spec']
        with kernel.db.transaction() as tx:
            if not tx.get(spec['module'],'module')['enabled']:raise Fault('module_disabled','能力已停用')
            kernel._permission(tx,spec,t['intent'],inp,None,'human',consume=True)
        return kernel.providers[cap]['handler']({**t,'input':inp},p,c)
    def execute(t,progress,cancel):
        plan=t['input'];sources=copy.deepcopy(plan['sources']);generated=[]
        for item in plan['reads']:
            r=item['resource'];cap='web.read' if 'url' in r else 'market.query'
            inp={'url':r['url']} if cap=='web.read' else {'text':r.get('market',plan['request'])}
            result=invoke(t,cap,inp,progress,cancel)
            for a in result['artifacts']:
                progress({'text':'读取完成：'+a['title'],'artifact':a})
                actual=kernel.db.get(t['id'],'task')['artifacts'][-1];saved=kernel.db.get(actual,'artifact')
                sources.append({'id':actual,'version':saved['version'],'title':a['title'],'source':a['content'].get('url',a['source']) if isinstance(a['content'],dict) else a['source'],'detail':r.get('detail','excerpt'),'text':source_text(saved,r.get('detail','excerpt'))})
            if sum(len(s['text']) for s in sources)>plan['budget']:raise Fault('source_budget','读取资料超出预算，请减少来源或使用原文片段')
        for action in plan['actions']:
            if cancel():raise Fault('cancelled','执行已停止')
            if action=='blank':text='';meta={'model':'local'}
            else:
                if not sources and action in ('write','research','compare','outline'):raise Fault('source_required','请先合并一份资料或行情泡泡')
                with kernel.db.transaction() as tx:
                    if any(s['id'] not in accessible(tx,t['intent']) for s in sources):raise Fault('scope_denied','资料访问权限已变化')
                    if not tx.get(kernel.providers['text.generate']['spec']['module'],'module')['enabled']:raise Fault('module_disabled','生成能力已停用')
                    if sum(len(s['text']) for s in sources)>plan['budget']:raise Fault('source_budget','本步骤输入超出预算，请减少来源或步骤')
                    kernel._permission(tx,kernel.providers['text.generate']['spec'],t['intent'],{'text':plan['request']},None,'human',consume=True)
                purpose=ACTIONS[action][1]+'。正文引用资料时用 [1]、[2] 编号。仅引用 sources 中存在的编号。不要自行输出来源列表或链接。'
                if action=='research':purpose+='如没有新闻资料，明确写“尚未添加新闻资料”。标注行情来源和报价时间，不编造最新消息或交易建议。'
                text,meta=generator.generate(json.dumps({'request':plan['request'],'constraints':plan['constraints'],'sources':[dict(s,number=i+1) for i,s in enumerate(sources)]},ensure_ascii=False),purpose,plan['runId']+'-'+str(len(generated)))
                validate_citations(text,sources)
            if cancel():raise Fault('cancelled','执行已停止')
            content={'text':text,'sources':copy.deepcopy(sources),'runId':plan['runId'],'canvasVersion':plan['canvasVersion'],'model':meta.get('model'),'usage':meta.get('usage',{})}
            a=artifact('document',ACTIONS[action][0],content,meta.get('model','local'));progress({'text':ACTIONS[action][0]+'完成','artifact':a});generated.append(a)
            if len(plan['actions'])>1:
                aid=kernel.db.get(t['id'],'task')['artifacts'][-1];saved=kernel.db.get(aid,'artifact')
                sources.append({'id':aid,'version':saved['version'],'title':a['title'],'source':a['source'],'detail':'full','text':text})
        return {'artifacts':[],'runId':plan['runId'],'sources':sources}
    register('bubble.suggest','寻找灵感',obj({'text':string()},['text']),suggest)
    register('bubble.merge','判断融合',obj({'text':string(),'left':{'type':'object'},'right':{'type':'object'}},['text','left','right']),merge)
    register('bubble.execute','运行组合',{'type':'object'},execute)
