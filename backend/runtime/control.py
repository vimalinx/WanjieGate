"""Semantic Control DAG: bounded typed decisions, never natural-language agents."""
import json
import re
from pathlib import Path
from .protocol import Fault, now, uid, validate

ROOT=Path(__file__).resolve().parents[2]/'protocol/v0.2'
THREADS=['CONTINUE','CORRECT','BRANCH','RETURN','NEW','MERGE','CLOSE']
OPERATIONS=['OBSERVE','RETRIEVE','CREATE','MODIFY','EXECUTE','COMMUNICATE','ORGANIZE','COMPARE','CONTROL']
PHASES=['EXPLORE','FORM','ACT','VERIFY','WAIT','HANDOFF']
ATTENTION=['FOREGROUND','EDGE','BACKGROUND','PARKED','INTERRUPT']
COMMITMENTS=['HYPOTHESIS','PREPARED','PREVIEW','READY','COMMITTED']
STAGES=['OBSERVE','ORIENT','LOCATE','INTERPRET','PREPARE','COMPOSE','COMMIT','EXECUTE','VERIFY','LEARN']


def contract(name):return json.loads((ROOT/'schemas'/f'{name}.schema.json').read_text())

def split_clauses(text):
    """Only explicit clause boundaries. No generated paraphrases or hidden LLM."""
    parts=[];start=0
    for match in re.finditer(r'[；;\n]+|[，,。]\s*(?=顺便|另外|哦对|还有|换个事)',text):
        if text[start:match.start()].strip():parts.append({'text':text[start:match.start()].strip(),'start':start,'end':match.start()})
        start=match.end()
    if text[start:].strip():parts.append({'text':text[start:].strip(),'start':start,'end':len(text)})
    return parts[:4],len(parts)>4


def facts(text,context):
    event=context.get('event') or {'type':'input.text','source':'capsule','text':text,'final':False}
    validate(event,contract('raw-event'))
    clauses,truncated=split_clauses(text)
    return {'event':event,'clauses':clauses or [{'text':text,'start':0,'end':len(text)}],
            'segmentationRequired':truncated,'selectedArtifact':context.get('selectedArtifact','')}


def candidates(context):
    intents=context.get('intentCandidates',[])[:8]
    targets=context.get('targetCandidates',context.get('items',[]))
    selected=context.get('selectedArtifact','')
    targets=sorted(targets,key=lambda a:(a.get('artifact')!=selected,{'HOT':0,'WARM':1,'COLD':2}.get(a.get('tier'),1)))[:12]
    return {'intents':intents,'targets':targets}


def choice(instruction,options):return {'type':'choice','instructions':instruction,'criteria':options}


def add_questions(body,context):
    observation=facts(body['state']['request'],context);pool=candidates(context)
    body['state']['observation']=observation
    body['state']['intentCandidates']=[{k:a[k] for k in ('id','title','goal') if k in a} for a in pool['intents']]
    body['state']['targetCandidates']=[{k:a[k] for k in ('artifact','title','kind','tier') if k in a} for a in pool['targets']]
    body['questions']={k:v for k,v in body['questions'].items() if k not in ('phase','new_thread','resume')}
    for index,segment in enumerate(observation['clauses']):
        prefix=f's{index}_';lead=f'Only classify observation.clauses[{index}].text. Other clauses are separate requests. '
        body['questions'][prefix+'relation']=choice(lead+'How does this relate to the existing goal?',dict(zip(THREADS,[
            '继续同一件事。Same goal, including changing work phase.','纠正或撤销刚才的要求。Correct or replace the forming request.',
            '顺手分出副任务或生活提醒，原事仍保留。A side task while keeping the current goal.',
            '回到一个已存在的其他任务。Return to another existing intent.',
            '明确开始无关的新目标。Start a genuinely unrelated goal.',
            '明确要求合并已有任务。Explicitly merge existing intents.','明确结束当前事情。Explicitly close this goal.'])))
        body['questions'][prefix+'operation']=choice(lead+'What operation is requested, independent of app or subject?',dict(zip(OPERATIONS,[
            '查看、展示或监听。Observe/display.','查找已有对象或资料。Retrieve existing information.',
            '产生新文稿、代码或对象。Create new content.','修改已有对象。Modify an existing object.',
            '运行程序、测试或动作。Execute an operation.','表达或发送给别人。Communicate with someone.',
            '保存、归类、整理或设置提醒。Organize, save or arrange a reminder.','比较几个对象或方案。Compare.',
            '暂停、返回、关闭或切换。Control work state.'])))
        body['questions'][prefix+'phase']=choice(lead+'What is the next work phase requested (not its domain)? Requesting the assistant to write counts as ACT. Testing correctness is VERIFY.',dict(zip(PHASES,[
            '搜集资料、理解、摸索。Gather and understand information.','形成方案、草稿构思、决策。Form a plan or approach.',
            '真正创建、写作、修改或执行。Actually create, write, modify or operate.','测试、检查结果正确性。Verify correctness.',
            '等待人、任务、网络或时间。Wait.','交接给别人或工作者。Hand work off.'])))
        body['questions'][prefix+'attention']=choice(lead+'What attention level is requested? Do not infer interruption solely from relevance.',dict(zip(ATTENTION,[
            '当前直接处理。Foreground.','放在边缘马上可能要用。At the edge of attention.','留在后台继续。Background.',
            '停放、暂不参与。Parked.','明确紧急且必须打断。Urgent interruption is required.'])))
        body['questions'][prefix+'commitment']=choice(lead+'How clear is the request? This is SOFT readiness only; never permission to execute.',{
            'HYPOTHESIS':'半句话、猜测或意图不清。Incomplete or speculative.',
            'PREPARED':'可以准备资源，还不能决定动作。Resources can be prepared.',
            'PREVIEW':'要求看看可能结果。Preview requested.',
            'READY':'请求足够明确，但执行仍需要独立授权。Clear request, still requires commit.'})
        body['questions'][prefix+'thread']=choice(lead+'Select the existing intent this clause refers to; NONE if new or unresolved.',{
            **{a['id']:a.get('title','')+' — '+a.get('goal','') for a in pool['intents']},'NONE':'没有匹配的已存在任务，或不能确定。'})
        body['questions'][prefix+'target']=choice(lead+'Select an explicitly referenced target from the available candidates. NONE for a new object or unresolved reference.',{
            **{a['artifact']:a.get('title','')+' ('+a.get('kind','')+')' for a in pool['targets']},'NONE':'目标尚不存在、未提供或无法确定。'})
        body['questions'][prefix+'actionable']={'type':'noul','instructions':lead+'Does this clause request a meaningful system action or preparation?'}
    body['questions']['compound']={'type':'noul','instructions':'Does the original request contain multiple independent goals (not just steps of the same goal)?'}
    return observation,pool


def selected_answer(data,key,options):
    a=data['answers'][key]
    if a['type']!='choice' or a['choice'] not in options:raise ValueError('Invalid choice: '+key)
    from .semantic import probability
    distribution=a['probabilities']
    if set(distribution)!=set(options) or abs(sum(probability(v) for v in distribution.values())-1)>.02:raise ValueError('Invalid distribution: '+key)
    probability(a['confidence'])
    return a['choice'],probability(distribution[a['choice']])


def compose(data,body,context):
    """All independent dimensions consume the SAME evaluated snapshot, one fan-out."""
    observation=body['state']['observation'];pool=candidates(context);frames=[];run_id=uid()
    from .semantic import probability
    compound=data['answers']['compound']
    if compound['type']!='noul':raise ValueError('Invalid compound answer')
    compound_score=probability(compound['noul'])
    nodes=[]
    def node(stage,inputs,outputs,status='complete'):
        record={'id':run_id+':'+stage,'stage':stage,'status':status,'inputs':inputs,'outputs':outputs,'timestamp':now()}
        validate(record,contract('node-'+stage.lower()));nodes.append(record)
    node('OBSERVE',{'event':observation['event']},{'clauses':observation['clauses'],'segmentationRequired':observation['segmentationRequired']})
    for index,segment in enumerate(observation['clauses']):
        prefix=f's{index}_';values={};confidence={}
        dimensions={'threadRelation':('relation',THREADS),'operation':('operation',OPERATIONS),'phase':('phase',PHASES),
                    'attention':('attention',ATTENTION),'commitment':('commitment',COMMITMENTS[:-1]),
                    'thread':('thread',[a['id'] for a in pool['intents']]+['NONE']),
                    'target':('target',[a['artifact'] for a in pool['targets']]+['NONE'])}
        for field,(key,options) in dimensions.items():values[field],confidence[field]=selected_answer(data,prefix+key,options)
        if observation['event']['type']=='asr.partial':
            values['commitment']='HYPOTHESIS'
        selected=context.get('selectedArtifact')
        if selected and any(a['artifact']==selected for a in pool['targets']):values['target']=selected;confidence['target']=1
        if values['threadRelation'] in ('CONTINUE','CORRECT','CLOSE'):
            values['thread']=context.get('intent','NONE')
        unresolved=[]
        if values['thread']=='NONE' and values['threadRelation'] in ('RETURN','MERGE'):unresolved.append('intent_candidates_exhausted')
        if values['target']=='NONE' and values['operation'] in ('MODIFY','EXECUTE'):unresolved.append('target_unresolved')
        if values['thread'] not in ('NONE',context.get('intent')):
            values['target']='NONE';unresolved.append('target_requires_thread_confirmation')
        if compound_score>=.8 and len(observation['clauses'])==1:unresolved.append('semantic_segmentation_required')
        if observation['segmentationRequired']:unresolved.append('clause_limit')
        frame={'id':uid(),'type':'frame','intent':context.get('intent','unbound'),'semanticVersion':'0.2','run':run_id,
               'segment':segment,**values,'confidence':confidence,'basedOnRevision':context.get('revision',0),
               'inputRevision':observation['event'].get('sequence',0),'unresolved':unresolved,'model':data['model'],
               'origin':'semantic','expiresAt':now()+30000,'evidence':[data.get('id','unknown')]}
        validate(frame,contract('intent-frame'));frames.append(frame)
    node('ORIENT',{'observation':'OBSERVE'},{'relations':[f['threadRelation'] for f in frames],'compoundness':compound_score,'providerCall':data.get('id')})
    node('LOCATE',{'candidates':{'intents':len(pool['intents']),'targets':len(pool['targets'])}},{'threads':[f['thread'] for f in frames],'targets':[f['target'] for f in frames],'unresolved':[r for f in frames for r in f['unresolved']]})
    node('INTERPRET',{'providerCall':data.get('id')},{'frames':[f['id'] for f in frames]})
    resources={'artifacts':[a['artifact'] for a in context['items']],'capabilities':[], 'memoryWrite':False}
    node('PREPARE',{'frames':[f['id'] for f in frames]},resources)
    node('COMPOSE',{'resources':resources},{'preview':[{'frame':f['id'],'attention':f['attention'],'phase':f['phase']} for f in frames]})
    node('COMMIT',{'readiness':[f['commitment'] for f in frames]},{'authorized':False,'reason':'semantic_readiness_is_not_permission'},'waiting')
    node('EXECUTE',{'commit':'COMMIT'},{'executed':False},'waiting')
    node('VERIFY',{'execute':'EXECUTE'},{'verified':False,'reason':'no_world_action'},'waiting')
    node('LEARN',{'frames':[f['id'] for f in frames]},{'retain':'trace_only','longTermMemoryWrite':False})
    result={'id':run_id,'semanticVersion':'0.2','frames':frames,'nodes':nodes,'compoundness':compound_score}
    validate(result,contract('control-run'));return result
