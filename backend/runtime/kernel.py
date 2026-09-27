"""Intent microkernel: commands, durable bus, registry, permissions and task lifecycle.

Only trusted in-process providers execute code. Browser clients can request commands,
never forge facts/signals or install executable modules. Replay reads state only.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import threading
from .protocol import VERSION, DIMENSIONS, TERMINAL, Fault, uid, now, validate, schema, message, ROOT
from .storage import Database, dump
from .context import build, projections, accessible
from .artifacts import validate_content

from .policies import POLICIES

class Kernel:
    def __init__(self, store, generator=None, market=None, semantic=None):
        self.store=store; self.db=Database(store.path)
        self.lock=threading.RLock(); self.pool=ThreadPoolExecutor(max_workers=3,thread_name_prefix='intent-task')
        self.providers={}; self.bindings={}; self.closed=False
        self.command_schemas=json.loads((ROOT/'commands.json').read_text())
        from .capabilities import install
        install(self,generator,market,semantic)
        self._migrate()
        with self.db.transaction() as tx:
            for task in tx.list('task'):
                if task['status'] not in TERMINAL:
                    task['status']='outcome_unknown' if task['status']=='running' else 'interrupted'
                    task['error']={'code':task['status'],'message':'服务重启；任务不会自动重放'}
                    task=tx.put(task)
                    tx.emit('task.recovered',{'task':task},task['intent'],task['command'])
            for policy in POLICIES:
                validate(policy,schema('policy'))

    def register(self, spec, manifest, handler):
        validate(spec,schema('capability')); validate(manifest,schema('manifest'))
        if spec['module']!=manifest['id'] or spec['id'] not in manifest['provides']:
            raise Fault('invalid_manifest','能力与模块声明不一致')
        if not manifest['trusted'] or spec['sideEffect']!=manifest['side_effect'] or spec['network']!=manifest['network'] or spec['cost']!=manifest['cost'] or set(spec['permissions'])!=set(manifest['permissions']):
            raise Fault('invalid_manifest','只加载可信模块，能力与 Manifest 的权限和副作用必须一致')
        self.providers[spec['id']]={'spec':spec,'manifest':manifest,'handler':handler}
        self.bindings.setdefault(spec['id'], {})[spec['module']]=self.providers[spec['id']]
        self.register_module(manifest)

    def register_module(self, manifest):
        validate(manifest,schema('manifest'))
        with self.db.transaction() as tx:
            try: old=tx.get(manifest['id'],'module')
            except Fault: old=None
            entity={'id':manifest['id'],'type':'module','manifest':manifest,'enabled':old['enabled'] if old else True,
                    'health':'ready','version':old['version'] if old else 0}
            tx.put(entity,create=old is None)

    def _migrate(self):
        with self.db.transaction() as tx:
            if tx.meta('migration.workspace.v1'):return
            for entry in self.store.workspaces():
                w=self.store.workspace(entry['id'])
                intent=self._new_intent(tx,w['title'],{'thread':w['title'],'goal':w['title']},id_=w['id'])
                intent['status']='suspended';intent=tx.put(intent)
                cause=tx.emit('intent.imported',{'intent':intent,'source':'legacy.workspace'},intent['id'])
                for a in w['artifacts']:
                    self._artifact(tx,intent['id'],{'title':a['title'],'kind':a['type'],'content':a['data'],
                        'source':a.get('source','legacy'),'pinned':a.get('pinned',False),
                        'version':a.get('version',0),'created':int(a.get('created',0)*1000) or now()},cause,id_=a['id'])
                if w.get('dataset'):
                    self._artifact(tx,intent['id'],{'title':w['dataset']['name'],'kind':'dataset','content':w['dataset'],'source':'legacy.dataset'},cause)
                for old in self.store.jobs(w['id']):
                    status={'complete':'success','failed':'failure','cancelled':'cancelled','interrupted':'interrupted',
                            'running':'outcome_unknown','queued':'interrupted'}.get(old['status'],'interrupted')
                    imported=message('command','capability.run',{'capability':'legacy.workbench','input':{'text':old.get('text','')}},'migration',w['id'],cause)
                    tx.append(imported)
                    task=tx.put({'id':old['id'],'type':'task','intent':w['id'],'capability':'legacy.workbench','provider':'legacy',
                        'status':status,'command':imported,'input':{'text':old.get('text','')},'context':{'items':[]},'grant':'',
                        'cancelRequested':False,'artifacts':old.get('artifacts',[]),'progress':[{'time':int(e.get('time',0)*1000),'text':e.get('text','')} for e in old.get('events',[])][-100:],
                        'fingerprint':'legacy:'+old['id'],'created':int(old.get('created',0)*1000) or now()},create=True)
                    if old.get('error'):task['error']={'code':'legacy','message':old['error']};task=tx.put(task)
                    tx.emit('task.recovered',{'task':task},w['id'],imported)
                    for a in w['artifacts']:
                        if a.get('job')==old['id']:self._relation(tx,w['id'],a['id'],'produced_by',old['id'],imported)
            tx.set_meta('migration.workspace.v1',True)

    def _new_intent(self,tx,title,state,parent='',id_=None):
        explicit = set(state)
        state={**dict.fromkeys(DIMENSIONS,''),'phase':'exploring','attention':'background','commitment':'considering',**state}
        e={'id':id_ or uid(),'type':'intent','title':title or '新的意图','state':state,'status':'warm','parent':parent,
           'fieldSources':{k:('human' if k in explicit else 'default') for k,v in state.items() if v},'preferences':{'contextBudget':12000,'autoRun':False,'localOnly':True}}
        return tx.put(e,create=True)

    def _artifact(self,tx,intent,p,cause,id_=None):
        validate_content(p['kind'],p['content'])
        e=tx.put({'id':id_ or uid(),'type':'artifact','kind':p['kind'],'title':p['title'],'content':p['content'],
                  'intent':intent,'source':p.get('source',cause['source']),'provenance':{'message':cause['id'],'correlationId':cause['correlationId']},
                  'pinned':p.get('pinned',False),'scope':p.get('scope','intent'),
                  'version':p.get('version',0),'created':p.get('created',now())},create=True)
        validate(e,schema('artifact'))
        tx.put({'id':intent+':'+e['id'],'type':'member','intent':intent,'artifact':e['id'],'tier':'HOT','pinned':False,'relevance':1,'reason':'当前产生或导入'},create=True)
        self._relation(tx,intent,e['id'],'belongs_to',intent,cause)
        tx.emit('artifact.created',{'artifact':e},intent,cause)
        return e

    def _relation(self,tx,intent,subject,predicate,object_,cause):
        for key in (subject,object_):
            e=tx.get(key)
            if e['type']=='intent' and key!=intent:raise Fault('scope_denied','关系不能跨未授权空间')
            if e['type']!='intent' and e.get('intent')!=intent and not (e['type']=='artifact' and e.get('scope')=='shared'):
                raise Fault('scope_denied','关系目标不在当前空间')
        id_=hashlib.sha256(dump([intent,subject,predicate,object_]).encode()).hexdigest()[:32]
        try:return tx.get(id_,'relation')
        except Fault:pass
        r=tx.put({'id':id_,'type':'relation','intent':intent,'subject':subject,'predicate':predicate,'object':object_,'source':cause['source']},create=True)
        tx.emit('relation.added',{'relation':r},intent,cause)
        return r

    def execute(self, command, principal='human'):
        try:
            return self._execute(command, principal)
        except Fault as exc:
            with self.db.transaction() as tx:
                tx.emit('command.rejected', {'code': exc.code, 'message': str(exc),
                    'requestedType': command.get('type') if isinstance(command, dict) else None},
                    intent=command.get('intent') if isinstance(command, dict) else None)
            raise

    def _execute(self, command, principal='human'):
        validate(command,schema('message'))
        command = {**command, 'correlationId': command.get('correlationId', command['id'])}
        if command['kind']!='command':raise Fault('message_kind_denied','客户端只能提交 Command')
        if command['source']!='renderer':raise Fault('source_denied','客户端来源必须是 renderer')
        type_=command['type']; p=command['payload']; intent_id=command.get('intent')
        if type_ not in self.command_schemas:raise Fault('unknown_command','未知命令')
        validate(p,self.command_schemas[type_])
        if command['timestamp']>now()+60000:raise Fault('invalid_timestamp','命令时间超出范围')
        if 'ttl' in command and now()>command['timestamp']+command['ttl']:raise Fault('expired','命令已过期')
        key=principal+':'+command.get('idempotencyKey',command['id'])
        fingerprint=hashlib.sha256(dump([type_,intent_id,p,command.get('expectedRevision')]).encode()).hexdigest()
        scheduled=None
        with self.lock:
            if self.closed:raise Fault('stopping','系统正在停止')
            with self.db.transaction() as tx:
                old=tx.db.execute('SELECT fingerprint,response FROM rt_commands WHERE key=?',(key,)).fetchone()
                if old:
                    if old['fingerprint']!=fingerprint:raise Fault('idempotency_conflict','同一命令编号不能用于不同内容')
                    return {**json.loads(old['response']),'duplicate':True}
                if type_ not in ('intent.create','session.start','module.set'):
                    if not intent_id:raise Fault('intent_required','需要选择意图空间')
                    intent=tx.get(intent_id,'intent')
                    if 'expectedRevision' in command and intent['version']!=command['expectedRevision']:
                        raise Fault('revision_conflict','意图已更新，请刷新')
                    if intent['status']=='archived' and type_!='intent.activate':raise Fault('intent_archived','请先恢复归档意图')
                tx.append(command)
                response,scheduled=self._dispatch(tx,command,principal)
                if scheduled is None:
                    result=tx.emit('command.completed',{'status':'success','value':response},intent_id,command,kind='result')
                    response={'result':result,'value':response}
                else:response={'task':response,'accepted':True}
                tx.db.execute('INSERT INTO rt_commands VALUES (?,?,?)',(key,fingerprint,dump(response)))
            if scheduled:self.pool.submit(self._run,scheduled)
        return response

    def _dispatch(self,tx,c,principal):
        t=c['type'];p=c['payload'];iid=c.get('intent')
        if t in ('intent.create','intent.fork'):
            parent=iid if t=='intent.fork' else p.get('parent','')
            if parent:tx.get(parent,'intent')
            i=self._new_intent(tx,p['title'],p.get('state',{}),parent)
            tx.emit('intent.created',{'intent':i},i['id'],c)
            return i,None
        if t=='session.start':
            candidates=sorted((i for i in tx.list('intent') if i['status']!='archived'),key=lambda i:i['updated'],reverse=True)[:5]
            return {'active':tx.meta('activeIntent'),'candidates':candidates},None
        if t.startswith('intent.'):
            i=tx.get(iid,'intent')
            if t=='intent.activate':
                for other in tx.list('intent'):
                    if other['id']!=iid and other['status']=='active':
                        other['status']='warm';other['state']['attention']='background';other=tx.put(other)
                        tx.emit('intent.warmed',{'intent':other},other['id'],c)
                i['status']='active';i['state']['attention']='foreground';tx.set_meta('activeIntent',iid)
            elif t=='intent.update':
                if 'title'in p:i['title']=p['title']
                i['state'].update(p.get('state',{}));i['fieldSources'].update({k:('human' if c['source']=='renderer' else 'semantic') for k in p.get('state',{})})
                i['preferences'].update(p.get('preferences',{}))
            elif t=='intent.warm':
                i['status']='warm';i['state']['attention']='background'
            else:
                i['status']='suspended' if t=='intent.suspend' else 'archived';i['state']['attention']='background'
                if tx.meta('activeIntent')==iid:tx.set_meta('activeIntent',None)
            i=tx.put(i);tx.emit({'intent.activate':'intent.activated','intent.update':'intent.updated',
                'intent.suspend':'intent.suspended','intent.archive':'intent.archived','intent.warm':'intent.warmed'}[t],{'intent':i},iid,c)
            return i,None
        if t=='artifact.create':return self._artifact(tx,iid,p,c),None
        if t=='artifact.update':
            a=tx.get(p['artifact'],'artifact');self._owned(a,iid)
            if a['version']!=p['version']:raise Fault('revision_conflict','内容已更新，请刷新后编辑')
            for k in ('title','content','pinned','scope'):
                if k in p:a[k]=p[k]
            validate_content(a['kind'],a['content'])
            a=tx.put(a);validate(a,schema('artifact'));tx.emit('artifact.updated',{'artifact':a},iid,c)
            return a,None
        if t=='relation.add':return self._relation(tx,iid,p['subject'],p['predicate'],p['object'],c),None
        if t=='relation.remove':
            r=tx.get(p['relation'],'relation');self._owned(r,iid);tx.remove(r['id']);tx.emit('relation.removed',{'relation':r['id']},iid,c)
            return {'removed':r['id']},None
        if t=='context.set':
            a=tx.get(p['artifact'],'artifact')
            if a['intent']!=iid and a['scope']!='shared':raise Fault('scope_denied','内容未共享到其他意图')
            mid=iid+':'+a['id']
            try:m=tx.get(mid,'member');create=False
            except Fault:m={'id':mid,'type':'member','intent':iid,'artifact':a['id'],'pinned':False};create=True
            if p['tier']=='COLD' and (a['pinned'] or m['pinned']) and p.get('pinned') is not False:raise Fault('pinned','请先取消固定')
            m.update(tier=p['tier'],pinned=p.get('pinned',m['pinned']),reason='用户选择' if c['source']=='renderer' else '语义相关性')
            if 'detail' in p:m['detail']=p['detail']
            m=tx.put(m,create=create);tx.emit('context.changed',{'member':m},iid,c)
            return m,None
        if t=='context.build':
            ctx=build(tx,iid);tx.emit('context.built',{'context':ctx},iid,c);return ctx,None
        if t=='view.set':
            if p['artifact'] not in accessible(tx,iid):raise Fault('scope_denied','内容不在当前空间')
            vid='view:'+iid+':'+p['artifact']
            try:v=tx.get(vid,'view');create=False
            except Fault:v={'id':vid,'type':'view','intent':iid,'state':{},'placement':'main'};create=True
            v.update(p);v=tx.put(v,create=create);validate(v,schema('view'));tx.emit('view.changed',{'view':v},iid,c)
            return v,None
        if t=='module.set':
            m=tx.get(p['module'],'module');m['enabled']=p['enabled'];m=tx.put(m)
            tx.emit('module.started' if m['enabled'] else 'module.stopped',{'module':m},cause=c)
            return m,None
        if t=='grant.create':
            if principal!='human':raise Fault('permission_denied','只有本机用户能授予权限')
            for cap in p['capabilities']:
                if cap not in self.providers:raise Fault('unknown_capability','授权包含未知能力')
            g=tx.put({'id':uid(),'type':'grant','intent':iid,'principal':principal,'capabilities':p['capabilities'],
                      'expiresAt':now()+p['expiresIn']*1000,'remaining':p['maxCalls'],'network':p['network'],
                      'maxEffect':p['maxEffect'],'inputEquals':p.get('inputEquals',{}),'reason':p['reason'],'revoked':False},create=True)
            tx.emit('permission.granted',{'grant':g},iid,c);return g,None
        if t=='grant.revoke':
            g=tx.get(p['grant'],'grant');self._owned(g,iid);g['revoked']=True;g=tx.put(g)
            tx.emit('permission.revoked',{'grant':g['id']},iid,c);return g,None
        if t=='task.cancel':
            task=tx.get(p['task'],'task');self._owned(task,iid)
            if task['status'] not in TERMINAL:
                task['cancelRequested']=True
                if task['status']=='queued':
                    self._finish(tx,task,'cancelled')
                    task=tx.get(task['id'],'task')
                else:task=tx.put(task)
                tx.emit('task.cancel.requested',{'task':task},iid,c)
            return task,None
        if t in ('capability.run','semantic.observe'):
            cap=p['capability'] if t=='capability.run' else 'semantic.observe'
            inp=p['input'] if t=='capability.run' else p
            if cap == 'semantic.observe':
                tx.set_meta('semantic.latest:' + iid, c['id'])
            return self._queue(tx,c,cap,inp,p.get('grant'),principal,p.get('provider'))
        if t=='notification.receive':
            n=tx.put({'id':uid(),'type':'notification','intent':iid,'title':p['title'],'text':p['text'],'source':p.get('source','human'),'status':'attached'},create=True)
            tx.emit('notification.received',{'notification':n},iid,c);return n,None
        if t=='notification.resolve':
            n=tx.get(p['notification'],'notification');self._owned(n,iid);n['status']={'attach':'attached','defer':'deferred','interrupt':'interrupt','read':'read'}[p['action']]
            n['manual']=c['source']=='renderer'
            n=tx.put(n);tx.emit('notification.routed',{'notification':n,'reason':c['source']},iid,c);return n,None
        raise Fault('unknown_command','未知命令')

    @staticmethod
    def _owned(entity,intent):
        if entity.get('intent')!=intent:raise Fault('scope_denied','对象不属于当前意图')

    def _permission(self,tx,spec,intent,inp,grant_id,principal,consume=False):
        i=tx.get(intent,'intent')
        if i['preferences'].get('localOnly') and spec['network']:raise Fault('local_only','仅本地模式禁止外部网络和云端生成')
        if spec['sideEffect']=='L0' and not spec['network'] and not spec['permissions']:return ''
        grants=[tx.get(grant_id,'grant')] if grant_id else tx.list('grant',intent)
        for g in grants:
            if (g['intent']!=intent or g['principal']!=principal or g['revoked'] or g['expiresAt']<=now()
                or g['remaining']<1 or spec['id'] not in g['capabilities'] or int(g['maxEffect'][1])<int(spec['sideEffect'][1])
                or (spec['network'] and not g['network']) or any(inp.get(k)!=v for k,v in g['inputEquals'].items())):continue
            if spec['sideEffect']=='L3' and g['inputEquals']!=inp:continue
            if consume:g['remaining']-=1;tx.put(g)
            return g['id']
        raise Fault('permission_required','需要为此能力授予当前意图的调用权限')

    def _queue(self,tx,c,cap,inp,grant,principal,provider=None):
        if cap not in self.providers:raise Fault('unknown_capability','能力不可用')
        candidates=self.bindings[cap]
        if provider and provider not in candidates:raise Fault('provider_unavailable','指定提供者不可用')
        selected=provider or next((key for key in sorted(candidates) if tx.get(key,'module')['enabled']),None)
        if not selected:raise Fault('module_disabled','此能力的提供者均已停用')
        spec=candidates[selected]['spec'];module=tx.get(spec['module'],'module')
        if not module['enabled']:raise Fault('module_disabled','模块已停用')
        validate(inp,spec['inputSchema'])
        active=[t for t in tx.list('task') if t['status'] not in TERMINAL]
        if len(active)>=12:raise Fault('queue_full','执行队列已满')
        if sum(t['intent']==c['intent'] for t in active)>=3:raise Fault('intent_busy','此意图最多同时接受三个任务')
        grant=self._permission(tx,spec,c['intent'],inp,grant,principal)
        ctx=build(tx,c['intent']);fingerprint=hashlib.sha256(dump([cap,inp,[(i['artifact'],i['version']) for i in ctx['items']]]).encode()).hexdigest()
        task=tx.put({'id':uid(),'type':'task','intent':c['intent'],'capability':cap,'provider':spec['module'],'status':'queued',
                     'command':c,'input':inp,'context':ctx,'grant':grant,'cancelRequested':False,'artifacts':[],'progress':[], 'fingerprint':fingerprint},create=True)
        validate(task,schema('task'));tx.emit('task.queued',{'task':task},c['intent'],c)
        return task,task['id']

    def _run(self,key):
        with self.db.transaction() as tx:
            task=tx.get(key,'task')
            if task['status']!='queued':return
            try:
                binding=self.bindings[task['capability']][task['provider']]
                spec=binding['spec']
                if not tx.get(spec['module'],'module')['enabled']:raise Fault('module_disabled','模块已停用')
                if tx.get(task['intent'],'intent')['status']=='archived':raise Fault('intent_archived','意图已归档')
                allowed=accessible(tx,task['intent'])
                members={m['artifact']:m for m in tx.list('member',task['intent'])}
                if any(item['artifact'] not in allowed or allowed[item['artifact']]['version']!=item['version'] or members.get(item['artifact'],{}).get('detail','full')!=item.get('detail','full') for item in task['context']['items']):
                    raise Fault('context_changed','排队期间上下文或共享权限已变化，请重新发起')
                self._permission(tx,spec,task['intent'],task['input'],task['grant'] or None,'human',consume=True)
            except Fault as exc:
                self._finish(tx,task,'failure',error={'code':exc.code,'message':str(exc)});return
            task['status']='running';task=tx.put(task);tx.emit('task.started',{'task':task},task['intent'],task['command'])
        try:
            output=binding['handler'](task,lambda data:self._progress(key,data),lambda:self.cancelled(key))
            validate(output,binding['spec']['outputSchema'])
            with self.db.transaction() as tx:
                current=tx.get(key,'task')
                if current['cancelRequested']:
                    self._finish(tx,current,'cancelled');return
                # Async semantic results may only apply to the state they observed.
                if task['capability']=='semantic.observe':self._signals(tx,current,output)
                for a in output.get('artifacts',[]):
                    artifact=self._artifact(tx,task['intent'],a,task['command'])
                    current['artifacts'].append(artifact['id'])
                    self._relation(tx,task['intent'],artifact['id'],'produced_by',key,task['command'])
                failed = output.get('exitCode', 0) != 0
                self._finish(tx,current,'failure' if failed else 'success',output,
                             {'code':'process_failed','message':'进程返回非零退出码，输出已保留'} if failed else None)
        except Exception as exc:
            from ..providers import ProviderError
            with self.db.transaction() as tx:
                current=tx.get(key,'task')
                status='cancelled' if current['cancelRequested'] else 'partial' if current['artifacts'] else 'outcome_unknown' if isinstance(exc,ProviderError) else 'failure'
                self._finish(tx,current,status,error={'code':getattr(exc,'code','provider_error' if isinstance(exc,ProviderError) else 'execution_failed'),'message':str(exc)[:500]})

    def _finish(self,tx,task,status,output=None,error=None):
        task['status']=status
        if output is not None:task['result']=output
        if error:task['error']=error
        task=tx.put(task)
        result=tx.emit('capability.result',{'status':status if status in ('success','partial','cancelled') else 'failure',
             'outcome':status,'task':task['id'],'artifacts':task['artifacts'],'error':error},task['intent'],task['command'],kind='result')
        tx.emit('task.finished',{'task':task},task['intent'],result)

    def _progress(self,key,data):
        with self.db.transaction() as tx:
            task=tx.get(key,'task')
            if task['cancelRequested']:raise Fault('cancelled','任务已停止')
            if 'artifact'in data:
                a=self._artifact(tx,task['intent'],data['artifact'],task['command']);task['artifacts'].append(a['id'])
                self._relation(tx,task['intent'],a['id'],'produced_by',key,task['command'])
            task['progress'].append({'time':now(),'text':data.get('text','阶段完成')});task=tx.put(task)
            tx.emit('task.progress',{'task':task},task['intent'],task['command'])

    def cancelled(self,key):
        return self.closed or self.db.get(key,'task')['cancelRequested']

    def _signals(self,tx,task,output):
        from .policies import apply
        apply(self,tx,task,output)

    def snapshot(self,intent=None):
        with self.db.transaction() as tx:
            intents=tx.list('intent');iid=intent or tx.meta('activeIntent')
            result={'protocolVersion':VERSION,'activeIntent':tx.meta('activeIntent'),'intents':intents,
                    'modules':tx.list('module'),'capabilities':[p['spec'] for p in self.providers.values()],'policies':POLICIES,
                    'cursor':tx.db.execute('SELECT COALESCE(MAX(seq),0) FROM rt_messages').fetchone()[0]}
            if iid:
                i=tx.get(iid,'intent')
                result.update(intent=i,artifacts=list(accessible(tx,iid).values()),tasks=tx.list('task',iid),
                              relations=tx.list('relation',iid),members=tx.list('member',iid),views=projections(tx,iid),
                              context=build(tx,iid),grants=tx.list('grant',iid),notifications=tx.list('notification',iid))
            return result

    def shutdown(self):
        with self.lock:self.closed=True
        self.pool.shutdown(wait=True,cancel_futures=True)
