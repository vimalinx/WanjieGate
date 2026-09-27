"""Replaceable deterministic policy module. Semantic values never execute tools."""
from .protocol import Fault, now, message, schema, validate
from .context import accessible

POLICIES=[
 {'id':'intent.phase','version':'0.1','accepts':['signal.intent.phase'],'threshold':.8,'action':'intent.update','automatic':True},
 {'id':'intent.continuity','version':'0.1','accepts':['signal.intent.continuity'],'threshold':.8,'action':'intent.fork','automatic':False},
 {'id':'artifact.relevance','version':'0.1','accepts':['signal.artifact.relevance'],'threshold':.8,'action':'context.set','automatic':True},
 {'id':'notification.relevance','version':'0.1','accepts':['signal.notification.relevance'],'threshold':.8,'action':'notification.resolve','automatic':True},
 {'id':'capability.selection','version':'0.1','accepts':['signal.capability.selection'],'threshold':.8,'action':'capability.suggest','automatic':False},
 {'id':'intent.resume','version':'0.1','accepts':['signal.intent.resume'],'threshold':.8,'action':'intent.warm','automatic':True}]

def apply(kernel,tx,task,output):
    iid=task['intent'];intent=tx.get(iid,'intent');base=task['context']['revision']
    stale=base!=intent['version'] or tx.meta('semantic.latest:'+iid)!=task['command']['id']
    stale=stale or tx.meta('control.input:'+iid) not in (None,task['command']['id'])
    observed=task['input'].get('event',{})
    if observed.get('stream'):
        stale=stale or tx.meta('event.sequence:'+iid+':'+observed['stream'])!=observed.get('sequence',0)
    current=accessible(tx,iid)
    members={m['artifact']:m for m in tx.list('member',iid)}
    stale=stale or any(item['artifact'] not in current or current[item['artifact']]['version']!=item['version'] or members.get(item['artifact'],{}).get('detail','full')!=item.get('detail','full') for item in task['context']['items'])
    if 'control' in output:
        from .control import contract
        validate(output['control'],contract('control-run'))
        if not stale:
            for frame in output['control']['frames']:tx.put(frame,create=True)
        tx.emit('control.completed',{'run':output['control'],'stale':stale},iid,task['command'])
    for raw in output.get('signals',[]):
        s={**raw,'basedOnRevision':base,'expiresAt':now()+30000,'operator':task['provider'],'evidence':[task['command']['id']]}
        validate(s,schema('signal'))
        signal=tx.emit(s['name'],s,iid,task['command'],kind='signal',source=task['provider'])
        d={'policy':s['name'],'version':'0.1','signal':signal['id'],'basedOnRevision':base,'action':'none','reason':'below_threshold'}
        action=None;payload=None
        policy_enabled=tx.get('builtin.policy','module')['enabled']
        if not policy_enabled:d['reason']='policy_disabled'
        elif stale:d['reason']='stale_revision'
        elif s['score']>=.8:
            if s['name']=='intent.phase':
                if intent['fieldSources'].get('phase')=='human':d['reason']='explicit_user_value'
                elif s['value'] in ('implementation','researching','planning','writing','exploring','EXPLORE','FORM','ACT','VERIFY','WAIT','HANDOFF'):
                    if s['value']==intent['state']['phase']:d['reason']='already_current'
                    else:action='intent.update';payload={'state':{'phase':s['value']}};d['reason']='phase_match'
            elif s['name']=='intent.frame':
                frame=s['value']
                d.update(action='preview_frame',reason='soft_state_only',frame=frame['id'])
            elif s['name']=='intent.continuity' and s['value']=='new':d.update(action='suggest_fork',reason='new_thread_candidate')
            elif s['name']=='capability.selection' and isinstance(s['value'],list):
                d.update(action='suggest_capabilities',reason='semantic_rank',candidates=[v for v in s['value'] if isinstance(v,dict) and v.get('capability') in kernel.providers and isinstance(v.get('score'),(int,float)) and v['score']>=.58])
            elif s['name']=='intent.resume' and s['value'] is True:
                if intent['status']=='suspended':action='intent.warm';payload={};d['reason']='resume_candidate'
            elif s['name']=='artifact.relevance' and isinstance(s['value'],dict):
                try:
                    a=tx.get(s['value']['artifact'],'artifact');m=tx.get(iid+':'+a['id'],'member')
                    dependencies={i['artifact'] for t in tx.list('task',iid) if t['status'] in ('queued','running') and t['id']!=task['id'] for i in t['context']['items']}
                    if a['pinned'] or m.get('pinned') or a['id'] in dependencies:d['reason']='protected_artifact'
                    elif m.get('reason')=='用户选择':d['reason']='explicit_user_value'
                    else:
                        relevant=s['value'].get('relevant',True)
                        tier='HOT' if relevant else 'WARM' if m['tier']=='HOT' else 'COLD'
                        if tier!=m['tier']:action='context.set';payload={'artifact':a['id'],'tier':tier};d['reason']='relevance_changed'
                except (Fault,KeyError):d['reason']='missing_artifact'
            elif s['name']=='notification.relevance' and isinstance(s['value'],dict):
                try:
                    n=tx.get(s['value']['notification'],'notification');kernel._owned(n,iid)
                    if n['status']=='read' or n.get('manual'):d['reason']='explicit_user_value'
                    else:
                        route='attach' if s['value'].get('relevant') else 'defer'
                        if s['value'].get('urgent') is True:route='interrupt'
                        action='notification.resolve';payload={'notification':n['id'],'action':route};d['reason']='relevance_and_independent_urgency'
                except (Fault,KeyError):d['reason']='missing_notification'
        if action:
            d['action']=action
            command=message('command',action,payload,'builtin.policy',iid,signal)
            validate(payload,kernel.command_schemas[action]);tx.append(command)
            result,queued=kernel._dispatch(tx,command,'policy')
            if queued is not None:raise Fault('policy_side_effect','语义策略不能直接启动执行')
            tx.emit('command.completed',{'status':'success','value':result},iid,command,kind='result',source='builtin.policy')
            intent=tx.get(iid,'intent')
        tx.emit('policy.evaluated',d,iid,signal,source='builtin.policy')

    if 'control' in output and not stale:
        for frame in output['control']['frames']:
            stored=tx.get(frame['id'],'frame');stored['acceptedRevision']=tx.get(iid,'intent')['version'];stored['acceptedInput']=task['command']['id'];tx.put(stored)
