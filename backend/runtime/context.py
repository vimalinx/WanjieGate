"""Deterministic working set and view projections; no model or I/O here."""
import json
from .protocol import Fault, now

PRIMITIVES={'document':'Text','note':'Text','memory':'Text','code':'Code','terminal':'Terminal',
            'web':'Web','image':'Media','video':'Media','audio':'Media','analysis':'Table','dataset':'Table',
            'tasks':'Timeline','scene':'Canvas','notification':'Conversation','repo':'Inspector'}

def accessible(tx, intent):
    own={a['id']:a for a in tx.list('artifact') if a['intent']==intent}
    for member in tx.list('member',intent):
        try:a=tx.get(member['artifact'],'artifact')
        except Fault:continue
        if a['scope']=='shared':own[a['id']]=a
    return own

def build(tx, intent_id):
    intent=tx.get(intent_id,'intent'); budget=intent.get('preferences',{}).get('contextBudget',12000)
    members={m['artifact']:m for m in tx.list('member',intent_id)}
    active={a for t in tx.list('task',intent_id) if t['status'] in ('queued','running') for a in [x['artifact'] for x in t.get('context',{}).get('items',[])]}
    candidates=[]
    for a in accessible(tx,intent_id).values():
        member=members.get(a['id'],{}); tier=member.get('tier','WARM')
        pinned=a.get('pinned',False) or member.get('pinned',False) or a['id'] in active
        score=member.get('relevance',0.5)
        reason='固定或执行依赖' if pinned else member.get('reason','当前空间内容')
        candidates.append((not pinned,{'HOT':0,'WARM':1,'COLD':2}[tier],-score,-a['updated'],a,reason,tier))
    selected=[]; excluded=[]; used=0
    for unpinned,_,_,_,a,reason,tier in sorted(candidates,key=lambda x:x[:4]):
        serialized=json.dumps(a['content'],ensure_ascii=False)
        detail=members.get(a['id'],{}).get('detail','full')
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
                         'tier':tier,'reason':reason,'cost':cost,'content':content,'source':a['source'],'detail':detail,'truncated':truncated,'originalCost':len(serialized)})
    return {'intent':intent_id,'revision':intent['version'],'budget':budget,'used':used,'items':selected,'excluded':excluded,'builtAt':now()}

def projections(tx,intent_id):
    intent=tx.get(intent_id,'intent'); phase=intent['state'].get('phase','')
    overrides={v['artifact']:v for v in tx.list('view',intent_id)}
    members={m['artifact']:m for m in tx.list('member',intent_id)}
    views=[]
    for a in accessible(tx,intent_id).values():
        m=members.get(a['id'],{}); override=overrides.get(a['id'])
        placement='main'
        if not a['pinned'] and not m.get('pinned'):
            if m.get('tier')=='COLD':placement='hidden'
            elif phase in ('researching','EXPLORE') and a['kind'] in ('code','terminal'):placement='side'
            elif phase in ('implementation','ACT','VERIFY') and a['kind']=='web':placement='side'
        view={'id':'view:'+a['id'],'artifact':a['id'],'primitive':PRIMITIVES.get(a['kind'],'Inspector'),
              'placement':placement,'state':{},**(override or {})}
        if not tx.get('builtin.view.'+view['primitive'],'module')['enabled']:
            view['placement']='hidden'
        views.append(view)
    return views
