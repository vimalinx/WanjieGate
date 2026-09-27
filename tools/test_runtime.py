"""Protocol invariants and isolated runtime integration; no external calls."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from backend.store import Store
from backend.runtime import Kernel
from backend.runtime.protocol import Fault, message, schema, validate, now

class Generator:
    model='test-provider'
    def __init__(self):self.calls=[];self.gate=None;self.entered=threading.Event();self.failure=False
    def generate(self,prompt,purpose,key):
        self.calls.append(prompt);self.entered.set()
        if self.gate:self.gate.wait(3)
        if self.failure:
            from backend.providers import ProviderError
            raise ProviderError('outcome_unknown')
        return '真实适配器隔离测试内容',{'model':self.model,'receipt':key}
class Semantic:
    def __init__(self):self.gate=None;self.entered=threading.Event()
    def observe(self,text,context):
        self.entered.set()
        if self.gate:self.gate.wait(3)
        return {'artifacts':[],'signals':[{'name':'intent.phase','value':'researching','score':.95,'model':'test-operator'}]}

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'state.sqlite3')
        self.gen=Generator();self.semantic=Semantic();self.kernel=Kernel(self.store,self.gen,semantic=self.semantic)
        self.intent=self.call('intent.create',{'title':'架构工作','state':{'goal':'完成协议'}})['value']['id']
    def tearDown(self):
        if self.gen.gate:self.gen.gate.set()
        if self.semantic.gate:self.semantic.gate.set()
        self.kernel.shutdown();self.tmp.cleanup()
    def command(self,type_,payload=None,**kw):return message('command',type_,payload or {},'renderer',getattr(self,'intent',None),**kw)
    def call(self,type_,payload=None,**kw):return self.kernel.execute(self.command(type_,payload,**kw))
    def wait(self,task):
        for _ in range(500):
            current=self.kernel.db.get(task['id'],'task')
            if current['status'] not in ('queued','running'):return current
            time.sleep(.01)
        self.fail('task timed out')
    def run_cap(self,cap,inp):return self.wait(self.call('capability.run',{'capability':cap,'input':inp})['task'])
    def allow(self,caps,network=False,maxcalls=10,effect='L2',**extra):
        if network:self.call('intent.update',{'preferences':{'localOnly':False}})
        return self.call('grant.create',{'capabilities':caps,'expiresIn':60,'maxCalls':maxcalls,'network':network,'maxEffect':effect,'reason':'isolated test',**extra})['value']
    def artifact(self,title='事实',kind='memory',content=None):
        return self.call('artifact.create',{'title':title,'kind':kind,'content':content or {'text':'来源明确的记忆'}})['value']
    def test_published_entities_validate(self):
        a=self.artifact();validate(a,schema('artifact'));validate(self.kernel.db.get(self.intent),schema('intent'))
        snap=self.kernel.snapshot(self.intent);validate(snap['context'],schema('context'))
        for m in snap['modules']:validate(m['manifest'],schema('manifest'))
        for c in snap['capabilities']:validate(c,schema('capability'))
    def test_command_rejects_signal_spoof_and_unknown_fields(self):
        cmd=self.command('intent.activate');cmd['kind']='signal'
        with self.assertRaises(Fault):self.kernel.execute(cmd)
        with self.assertRaises(Fault):self.call('intent.update',{'evil':'x'})
        cmd=self.command('intent.activate');cmd['source']='kernel'
        with self.assertRaises(Fault):self.kernel.execute(cmd)
    def test_duplicate_is_one_mutation_and_conflict_is_rejected(self):
        cmd=self.command('artifact.create',{'kind':'note','title':'one','content':{'text':'one'}})
        first=self.kernel.execute(cmd);second=self.kernel.execute(cmd)
        self.assertEqual(first['value']['id'],second['value']['id']);self.assertTrue(second['duplicate'])
        cmd['payload']['title']='two'
        with self.assertRaises(Fault):self.kernel.execute(cmd)
        self.assertEqual(len(self.kernel.db.list('artifact',self.intent)),1)
    def test_wire_command_without_optional_correlation(self):
        cmd=self.command('capability.run',{'capability':'data.import','input':{'text':'a,b\nx,1\ny,2'}})
        del cmd['correlationId']
        task=self.wait(self.kernel.execute(cmd)['task'])
        self.assertEqual(task['status'],'success')
        self.assertEqual(task['command']['correlationId'],cmd['id'])
    def test_expired_and_optimistic_revision(self):
        cmd=self.command('intent.activate',ttl=1);cmd['timestamp']=now()-1000
        with self.assertRaises(Fault):self.kernel.execute(cmd)
        with self.assertRaises(Fault):self.call('intent.update',{'title':'new'},expectedRevision=99)
        a=self.artifact();self.call('artifact.update',{'artifact':a['id'],'version':0,'content':{'text':'edited'}})
        with self.assertRaises(Fault):self.call('artifact.update',{'artifact':a['id'],'version':0,'content':{'text':'stale'}})
    def test_lifecycle_fork_preserves_parent(self):
        self.call('intent.activate');parent=self.intent;a=self.artifact()
        child=self.call('intent.fork',{'title':'晚上充电','state':{'domain':'personal'}})['value']
        self.assertEqual(child['parent'],parent)
        self.intent=child['id'];self.call('intent.activate')
        self.assertEqual(self.kernel.db.get(parent)['status'],'warm');self.assertEqual(self.kernel.db.get(a['id'])['intent'],parent)
        self.call('intent.suspend');self.assertEqual(self.kernel.snapshot()['activeIntent'],None)
    def test_context_budget_cold_does_not_delete(self):
        a=self.artifact(content={'text':'x'*1000});self.call('context.set',{'artifact':a['id'],'tier':'COLD'})
        self.assertEqual(self.kernel.snapshot(self.intent)['context']['items'],[])
        self.assertEqual(self.kernel.db.get(a['id'])['content']['text'],'x'*1000)
        self.call('context.set',{'artifact':a['id'],'tier':'HOT'});self.call('intent.update',{'preferences':{'contextBudget':256}})
        self.assertEqual(self.kernel.snapshot(self.intent)['context']['excluded'][0]['reason'],'budget')
    def test_shared_reference_revocation_and_scope(self):
        a=self.artifact();parent=self.intent;self.intent=self.call('intent.create',{'title':'child'})['value']['id']
        with self.assertRaises(Fault):self.call('context.set',{'artifact':a['id'],'tier':'HOT'})
        self.kernel.execute(message('command','artifact.update',{'artifact':a['id'],'version':0,'scope':'shared'},'renderer',parent))
        self.call('context.set',{'artifact':a['id'],'tier':'HOT'});self.assertEqual(len(self.kernel.snapshot(self.intent)['artifacts']),1)
        with self.assertRaises(Fault):self.call('artifact.update',{'artifact':a['id'],'version':1,'title':'evil'})
        self.kernel.execute(message('command','artifact.update',{'artifact':a['id'],'version':1,'scope':'intent'},'renderer',parent))
        self.assertEqual(self.kernel.snapshot(self.intent)['artifacts'],[])
    def test_view_is_projection_of_same_artifact(self):
        a=self.artifact();self.call('view.set',{'artifact':a['id'],'primitive':'Inspector','placement':'side'})
        snap=self.kernel.snapshot(self.intent);self.assertEqual(snap['views'][0]['primitive'],'Inspector');self.assertEqual(len(snap['artifacts']),1)
    def test_relation_and_trace(self):
        a=self.artifact();b=self.artifact('决定');r=self.call('relation.add',{'subject':a['id'],'predicate':'supports','object':b['id']})
        messages=self.kernel.db.events(correlation=r['result']['correlationId'])
        self.assertEqual([m['kind'] for m in messages],['command','event','result'])
        self.assertEqual(messages[1]['causationId'],messages[0]['id'])
    def test_local_analysis_complete_loop(self):
        imported=self.run_cap('data.import',{'text':'日期,数量\n一,10\n二,15'})
        self.assertEqual(imported['status'],'success')
        result=self.run_cap('data.analyze',{'artifact':imported['artifacts'][0]})
        self.assertEqual(result['status'],'success');a=self.kernel.db.get(result['artifacts'][0]);self.assertEqual(a['content']['columns'][0]['total'],25)
        validate(result,schema('task'))
    def test_local_only_and_missing_grant_never_call_generator(self):
        with self.assertRaises(Fault):self.call('capability.run',{'capability':'text.generate','input':{'text':'hello'}})
        self.call('intent.update',{'preferences':{'localOnly':False}})
        with self.assertRaises(Fault):self.call('capability.run',{'capability':'text.generate','input':{'text':'hello'}})
        self.assertEqual(self.gen.calls,[])
    def test_grant_budget_and_revocation(self):
        g=self.allow(['text.generate'],True,1)
        self.assertEqual(self.run_cap('text.generate',{'text':'hello'})['status'],'success')
        with self.assertRaises(Fault):self.call('capability.run',{'capability':'text.generate','input':{'text':'again'}})
        self.assertEqual(len(self.gen.calls),1)
        g=self.allow(['text.generate'],True);self.call('grant.revoke',{'grant':g['id']})
        with self.assertRaises(Fault):self.call('capability.run',{'capability':'text.generate','input':{'text':'again'}})
    def test_constraints_and_duplicate_network_task(self):
        self.allow(['text.generate'],True,inputEquals={'text':'approved'})
        with self.assertRaises(Fault):self.call('capability.run',{'capability':'text.generate','input':{'text':'unapproved'}})
        cmd=self.command('capability.run',{'capability':'text.generate','input':{'text':'approved'}})
        task=self.kernel.execute(cmd)['task'];self.kernel.execute(cmd);self.wait(task)
        self.assertEqual(len(self.gen.calls),1)
    def test_cancel_suppresses_upstream_result(self):
        self.allow(['text.generate'],True);self.gen.gate=threading.Event()
        task=self.call('capability.run',{'capability':'text.generate','input':{'text':'hello'}})['task'];self.assertTrue(self.gen.entered.wait(1))
        self.call('task.cancel',{'task':task['id']});self.gen.gate.set();result=self.wait(task)
        self.assertEqual(result['status'],'cancelled');self.assertEqual(result['artifacts'],[])
    def test_unknown_outcome_not_replayed(self):
        self.allow(['text.generate'],True);self.gen.failure=True
        cmd=self.command('capability.run',{'capability':'text.generate','input':{'text':'hello'}})
        task=self.kernel.execute(cmd)['task'];self.assertEqual(self.wait(task)['status'],'outcome_unknown');self.kernel.execute(cmd);self.assertEqual(len(self.gen.calls),1)
    def test_stale_semantic_result_does_not_change_intent(self):
        self.semantic.gate=threading.Event();task=self.call('semantic.observe',{'text':'research'})['task'];self.assertTrue(self.semantic.entered.wait(1))
        self.call('intent.update',{'state':{'phase':'implementation'}});self.semantic.gate.set();self.wait(task)
        self.assertEqual(self.kernel.db.get(self.intent)['state']['phase'],'implementation')
        self.assertTrue(any(m['payload'].get('reason')=='stale_revision' for m in self.kernel.db.events(intent=self.intent)))
    def test_semantic_policy_changes_default_but_not_explicit_phase(self):
        self.wait(self.call('semantic.observe',{'text':'research'})['task']);self.assertEqual(self.kernel.db.get(self.intent)['state']['phase'],'researching')
        self.call('intent.update',{'state':{'phase':'implementation'}});self.wait(self.call('semantic.observe',{'text':'research'})['task'])
        self.assertEqual(self.kernel.db.get(self.intent)['state']['phase'],'implementation')
    def test_module_lifecycle_denies_new_tasks(self):
        self.call('module.set',{'module':'builtin.data.import','enabled':False})
        with self.assertRaises(Fault):self.call('capability.run',{'capability':'data.import','input':{'text':'a,b\nx,1\ny,2'}})
    def test_workflow_bindings_and_partial_failure(self):
        task=self.run_cap('workflow.run',{'steps':[{'id':'import','capability':'data.import','input':{'text':'a,b\nx,1\ny,2'}},
             {'id':'analyze','capability':'data.analyze','input':{},'dependsOn':['import'],'bindings':{'artifact':'import'}}]})
        self.assertEqual(task['status'],'success');self.assertEqual(len(task['artifacts']),2)
        failed=self.run_cap('workflow.run',{'steps':[{'id':'import','capability':'data.import','input':{'text':'a,b\nx,1\ny,2'}},
             {'id':'bad','capability':'data.analyze','input':{'artifact':'missing'},'dependsOn':['import']}]})
        self.assertEqual(failed['status'],'partial');self.assertEqual(len(failed['artifacts']),1)
    def test_restart_preserves_state_and_never_reexecutes(self):
        a=self.artifact();self.kernel.shutdown();self.kernel=Kernel(self.store,self.gen,semantic=self.semantic)
        self.assertEqual(self.kernel.db.get(a['id'])['title'],'事实');self.assertEqual(self.gen.calls,[])
    def test_legacy_migration_keeps_original(self):
        tmp=tempfile.TemporaryDirectory();store=Store(Path(tmp.name)/'old.sqlite3');w=store.new_workspace();a=store.put_artifact(w['id'],{'type':'document','title':'旧文稿','data':{'text':'保留'},'source':'legacy'})
        k=Kernel(store)
        try:
            self.assertEqual(k.db.get(a['id'])['content']['text'],'保留');self.assertEqual(store.workspace(w['id'])['artifacts'][0]['id'],a['id'])
        finally:k.shutdown();tmp.cleanup()
    def test_semantic_action_has_command_and_result_in_chain(self):
        task=self.wait(self.call('semantic.observe',{'text':'research'})['task'])
        events=self.kernel.db.events(correlation=task['command']['correlationId'])
        self.assertTrue(any(m['kind']=='command' and m['source']=='builtin.policy' for m in events))
        self.assertTrue(any(m['kind']=='result' and m['source']=='builtin.policy' for m in events))
    def test_invalid_artifact_edit_rolls_back(self):
        a=self.artifact(kind='tasks',content={'items':[{'id':'a','title':'完成','done':False}]})
        with self.assertRaises(Fault):self.call('artifact.update',{'artifact':a['id'],'version':0,'content':{'items':'bad'}})
        self.assertEqual(self.kernel.db.get(a['id'])['version'],0)
    def test_alternative_provider_selection(self):
        from copy import deepcopy
        original=self.kernel.providers['data.import'];spec=deepcopy(original['spec']);manifest=deepcopy(original['manifest'])
        spec['module']='alternative.import';manifest['id']='alternative.import'
        self.kernel.register(spec,manifest,lambda t,p,c:{'artifacts':[],'alternative':True})
        task=self.wait(self.call('capability.run',{'capability':'data.import','provider':'alternative.import','input':{'text':'ignored'}})['task'])
        self.assertTrue(task['result']['alternative']);self.assertEqual(task['provider'],'alternative.import')
    def test_stopped_view_does_not_delete_artifact(self):
        a=self.artifact();self.call('module.set',{'module':'builtin.view.Text','enabled':False})
        state=self.kernel.snapshot(self.intent);self.assertEqual(state['views'][0]['placement'],'hidden');self.assertEqual(state['artifacts'][0]['id'],a['id'])
    def test_operator_replacement_notification_policy(self):
        n=self.call('notification.receive',{'title':'无关提醒','text':'稍后处理'})['value']
        self.semantic.observe=lambda text,context:{'artifacts':[],'signals':[{'name':'notification.relevance','value':{'notification':n['id'],'relevant':False,'interruptible':False},'score':.96,'model':'test'}]}
        self.wait(self.call('semantic.observe',{'text':'专注当前目标'})['task'])
        self.assertEqual(self.kernel.db.get(n['id'])['status'],'deferred')
    def test_disabled_policy_keeps_signal_but_does_not_act(self):
        self.call('module.set',{'module':'builtin.policy','enabled':False})
        self.wait(self.call('semantic.observe',{'text':'research'})['task'])
        self.assertEqual(self.kernel.db.get(self.intent)['state']['phase'],'exploring')
    def test_resource_execution_in_sandbox(self):
        import shutil
        if not shutil.which('bwrap') or not shutil.which('prlimit'):self.skipTest('sandbox prerequisites unavailable')
        self.allow(['code.run'])
        task=self.run_cap('code.run',{'code':"from pathlib import Path; print(10+15); print(Path('/home/vimalinx').exists())"})
        if task['status']!='success':
            content=self.kernel.db.get(task['artifacts'][0])['content']['text'] if task['artifacts'] else str(task.get('error'))
            self.fail('sandbox failed: '+content)
        content=self.kernel.db.get(task['artifacts'][0])['content'];self.assertEqual(content['text'],'25\nFalse\n')
    def test_restart_marks_running_unknown_and_queued_interrupted(self):
        t=self.run_cap('data.import',{'text':'a,b\nx,1\ny,2'})
        with self.kernel.db.transaction() as tx:
            running=tx.get(t['id']);running['status']='running';tx.put(running)
        self.kernel.shutdown();self.kernel=Kernel(self.store,self.gen,semantic=self.semantic)
        self.assertEqual(self.kernel.db.get(t['id'])['status'],'outcome_unknown')
        with self.kernel.db.transaction() as tx:
            queued=tx.get(t['id']);queued['status']='queued';tx.put(queued)
        self.kernel.shutdown();self.kernel=Kernel(self.store,self.gen,semantic=self.semantic)
        self.assertEqual(self.kernel.db.get(t['id'])['status'],'interrupted');self.assertEqual(len(self.kernel.db.list('artifact',self.intent)),1)
    def test_project_paths_reject_secrets_and_escape(self):
        from backend.runtime.capabilities import project_file
        for path in ('../LocalRouter/README.md','.data/receipts/request.json','/etc/passwd','.ai/live-smoke/request.json'):
            with self.assertRaises(Fault):project_file(path)

    def test_context_detail_preserves_original_and_marks_excerpt(self):
        a=self.artifact(content={'text':'x'*2000})
        self.call('context.set',{'artifact':a['id'],'tier':'WARM','detail':'excerpt'})
        item=self.kernel.snapshot(self.intent)['context']['items'][0]
        self.assertEqual(item['detail'],'excerpt');self.assertTrue(item['truncated'])
        self.assertEqual(item['content']['excerpt'],'x'*1200)
        self.assertLess(item['cost'],item['originalCost'])
        self.call('context.set',{'artifact':a['id'],'tier':'HOT','detail':'metadata'})
        item=self.kernel.snapshot(self.intent)['context']['items'][0]
        self.assertNotIn('text',item['content']);self.assertEqual(item['content']['artifact'],a['id'])
        self.assertEqual(self.kernel.db.get(a['id'])['content']['text'],'x'*2000)
        self.call('context.set',{'artifact':a['id'],'tier':'HOT','detail':'full'})
        self.assertEqual(self.kernel.snapshot(self.intent)['context']['items'][0]['content']['text'],'x'*2000)
    def test_queued_context_change_does_not_consume_grant(self):
        from unittest.mock import patch
        a=self.artifact();g=self.allow(['text.generate'],True,maxcalls=1)
        with patch.object(self.kernel.pool,'submit'):
            t=self.call('capability.run',{'capability':'text.generate','input':{'text':'use context'}})['task']
        self.call('context.set',{'artifact':a['id'],'tier':'HOT','detail':'metadata'})
        self.kernel._run(t['id']);result=self.kernel.db.get(t['id'])
        self.assertEqual(result['error']['code'],'context_changed')
        self.assertEqual(self.kernel.db.get(g['id'])['remaining'],1);self.assertEqual(self.gen.calls,[])
    def test_semantic_content_and_detail_changes_make_result_stale(self):
        a=self.artifact()
        for change in ('content','detail'):
            self.semantic.entered.clear();self.semantic.gate=threading.Event()
            t=self.call('semantic.observe',{'text':'research '+change})['task']
            self.assertTrue(self.semantic.entered.wait(1))
            if change=='content':self.call('artifact.update',{'artifact':a['id'],'version':0,'content':{'text':'updated'}})
            else:self.call('context.set',{'artifact':a['id'],'tier':'HOT','detail':'metadata'})
            self.semantic.gate.set();self.wait(t)
            self.assertEqual(self.kernel.db.get(self.intent)['state']['phase'],'exploring')
            decisions=[m for m in self.kernel.db.events(correlation=t['command']['correlationId']) if m['type']=='policy.evaluated']
            self.assertEqual(decisions[0]['payload']['reason'],'stale_revision')
    def test_workflow_nonzero_exit_stops_following_steps(self):
        self.kernel.providers['data.import']['handler']=lambda t,p,c:{'artifacts':[{'kind':'terminal','title':'failed output','content':{'text':'failed','exitCode':7},'source':'test'}],'exitCode':7}
        t=self.run_cap('workflow.run',{'steps':[{'id':'first','capability':'data.import','input':{'text':'ignored'}},{'id':'later','capability':'data.import','input':{'text':'ignored'},'dependsOn':['first']}]})
        self.assertEqual(t['status'],'partial');self.assertEqual(t['error']['code'],'process_failed')
        self.assertEqual(len(t['artifacts']),1)
        starts=[m for m in self.kernel.db.events(correlation=t['command']['correlationId']) if m['type']=='workflow.step.started']
        self.assertEqual([m['payload']['step'] for m in starts],['first'])

    def test_legacy_jobs_migrate_with_private_backup(self):
        from backend.server import create_server
        import sqlite3
        with tempfile.TemporaryDirectory() as root:
            store=Store(Path(root)/'workspaces.sqlite3');w=store.new_workspace()
            for status in ('complete','running','queued'):
                store.save_job({'id':'legacy-'+status,'workspace':w['id'],'request_id':'request-'+status,'status':status,'created':time.time(),'text':'old','artifacts':[],'events':[]})
            server=create_server(0,root)
            try:
                backups=list((Path(root)/'backups').glob('*.sqlite3'));self.assertEqual(len(backups),1)
                self.assertEqual(backups[0].stat().st_mode & 0o777,0o600)
                with sqlite3.connect(backups[0]) as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],3)
                    self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='rt_entities'").fetchone())
                for before,after in [('complete','success'),('running','outcome_unknown'),('queued','interrupted')]:
                    self.assertEqual(server.kernel.db.get('legacy-'+before)['status'],after)
                self.assertEqual(len(store.jobs(w['id'])),3)
            finally:server.kernel.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
