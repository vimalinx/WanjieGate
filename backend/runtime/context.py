"""Deterministic working set and view projections; no model or I/O here."""
import json
from .protocol import now
from .object_graph import accessible, effective_relations, primary_members, stored_relations, DEFAULT_ROLE, relation_id

PRIMITIVES={'document':'Text','note':'Text','memory':'Text','code':'Code','terminal':'Terminal',
            'web':'Web','image':'Media','video':'Media','audio':'Media','analysis':'Table','dataset':'Table',
            'tasks':'Timeline','scene':'Canvas','notification':'Conversation','repo':'Inspector'}

def detail_for(artifact,member):
    return 'metadata' if artifact['kind'] in ('image','audio','video') else member.get('detail','full')

def build(tx, intent_id):
    intent=tx.get(intent_id,'intent'); budget=intent.get('preferences',{}).get('contextBudget',12000)
    members=primary_members(tx,intent_id)
    relations=effective_relations(tx,intent_id)
    known={m['artifact'] for m in stored_relations(tx,intent_id)}
    active={a for t in tx.list('task',intent_id) if t['status'] in ('queued','running') for a in [x['artifact'] for x in t.get('context',{}).get('items',[])]}
    candidates=[]
    for a in accessible(tx,intent_id).values():
        if a['id'] in known and a['id'] not in members:continue
        member=members.get(a['id'],{}); tier=member.get('tier','WARM')
        pinned=a.get('pinned',False) or member.get('pinned',False) or a['id'] in active
        score=member.get('relevance',0.5)
        reason='固定或执行依赖' if pinned else member.get('reason','当前空间内容')
        candidates.append((not pinned,{'HOT':0,'WARM':1,'COLD':2}[tier],-score,-a['updated'],a,reason,tier))
    selected=[]; excluded=[]; used=0
    for unpinned,_,_,_,a,reason,tier in sorted(candidates,key=lambda x:x[:4]):
        serialized=json.dumps(a['content'],ensure_ascii=False)
        detail=detail_for(a,members.get(a['id'],{}))
        content=a['content'];truncated=False
        if detail=='metadata':content={'artifact':a['id'],'title':a['title'],'kind':a['kind'],'source':a['source']}
        elif detail=='excerpt':
            text=a['content'].get('text') if isinstance(a['content'],dict) else a['content']
            text=text if isinstance(text,str) else serialized
            truncated=len(text)>1200
            content={'excerpt':text[:1200],'truncated':truncated,'representation':'verbatim-prefix'}
        cost=len(json.dumps(content,ensure_ascii=False))
        if tier=='COLD' and unpinned:
            excluded.append({'artifact':a['id'],'reason':'COLD'});continue
        if used+cost>budget:
            excluded.append({'artifact':a['id'],'reason':'budget','pinned':not unpinned});continue
        used+=cost
        selected.append({'artifact':a['id'],'version':a['version'],'kind':a['kind'],'title':a['title'],
                         'tier':tier,'reason':reason,'cost':cost,'content':content,'source':a['source'],'detail':detail,'truncated':truncated,'originalCost':len(serialized),
                         'roles':[m['role'] for m in relations if m['artifact']==a['id']],
                         'contextRelations':[m for m in relations if m['artifact']==a['id']]})
    return {'intent':intent_id,'revision':intent['version'],'budget':budget,'used':used,'items':selected,'excluded':excluded,'builtAt':now()}

def projections(tx,intent_id):
    intent=tx.get(intent_id,'intent'); phase=intent['state'].get('phase','')
    overrides={(v['artifact'],v.get('role',DEFAULT_ROLE)):v for v in tx.list('view',intent_id)}
    relations=effective_relations(tx,intent_id)
    known={m['artifact'] for m in stored_relations(tx,intent_id)}
    views=[]
    for a in accessible(tx,intent_id).values():
        roles=[m for m in relations if m['artifact']==a['id']]
        if not roles and a['id'] in known:continue
        for m in roles or [{'role':DEFAULT_ROLE,'localProperties':{}}]:
            role=m['role'];override=overrides.get((a['id'],role))
            placement='main'
            if not a['pinned'] and not m.get('pinned'):
                if m.get('tier')=='COLD':placement='hidden'
                elif phase in ('researching','EXPLORE') and a['kind'] in ('code','terminal'):placement='side'
                elif phase in ('implementation','ACT','VERIFY') and a['kind']=='web':placement='side'
            primitive={'reference':'Inspector','source':'Inspector','task':'Timeline'}.get(role,PRIMITIVES.get(a['kind'],'Inspector'))
            view={'id':'view:'+relation_id(intent_id,a['id'],role),
                  'artifact':a['id'],'primitive':primitive,'role':role,'contextRelation':m.get('id'),
                  'localProperties':m['localProperties'],'placement':placement,'state':{},**(override or {})}
            if not tx.get('builtin.view.'+view['primitive'],'module')['enabled']:
                view['placement']='hidden'
            views.append(view)
    return views
