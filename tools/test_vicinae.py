import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

class VicinaeTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('backend.vicinae'), 'Vicinae bridge is missing')
        from backend import vicinae
        return vicinae

    def test_catalog_excludes_unreviewed_actions_and_keeps_live_ids(self):
        m=self.module()
        rows=[{'id':'files:search','name':'搜索文件'},{'id':'power:power-off','name':'关闭系统'},{'id':'extension:unknown','name':'未知扩展'}]
        with patch('subprocess.run',return_value=subprocess.CompletedProcess([],0,json.dumps(rows),'')):
            bridge=m.VicinaeBridge('/fake/cli')
            items=bridge.candidates('找昨天的资料')
        self.assertEqual([x['resource']['command'] for x in items],['files:search'])
        self.assertEqual(items[0]['resource']['query'],'')
        with patch('subprocess.run',return_value=subprocess.CompletedProcess([],0,json.dumps(rows),'')):
            named=m.VicinaeBridge('/fake/cli').candidates('查找“年度报告.pdf”')
        self.assertEqual(named[0]['resource']['query'],'年度报告.pdf')

    def test_installed_application_is_a_candidate_and_launches_without_query(self):
        m=self.module();calls=[]
        rows=[{'id':'applications:com.tencent.xinWeChat','name':'微信'},
              {'id':'applications:com.apple.Notes','name':'备忘录'},
              {'id':'power:power-off','name':'关闭微信'}]
        def run(argv,**kw):
            calls.append(argv)
            return subprocess.CompletedProcess(argv,0,json.dumps(rows) if 'ls' in argv else '', '')
        with patch('subprocess.run',side_effect=run):
            bridge=m.VicinaeBridge('/fake/cli')
            for text in ['帮我打开微信','open WeChat']:
                items=bridge.candidates(text)
                self.assertEqual([x['resource']['command'] for x in items],['applications:com.tencent.xinWeChat'])
                self.assertEqual(items[0]['title'],'打开微信')
            result=bridge.launch('applications:com.tencent.xinWeChat','do not forward this')
            self.assertEqual(result['status'],'handed_off')
            self.assertEqual(calls[-1],['/fake/cli','cmd','launch','applications:com.tencent.xinWeChat'])
            with self.assertRaises(ValueError):bridge.launch('applications:com.fake.Missing','')

    def test_query_is_passed_as_one_argument_not_shell_text(self):
        m=self.module();calls=[]
        def run(argv,**kw):
            self.assertNotIn('shell',kw);calls.append(argv)
            return subprocess.CompletedProcess(argv,0,json.dumps([{'id':'files:search','name':'文件'}]) if 'ls' in argv else '', '')
        with patch('subprocess.run',side_effect=run):
            bridge=m.VicinaeBridge('/fake/cli')
            result=bridge.launch('files:search','a; $(touch /tmp/never)')
        self.assertEqual(calls[-1],['/fake/cli','cmd','launch','files:search','--query','a; $(touch /tmp/never)'])
        self.assertEqual(result['status'],'handed_off')
        self.assertFalse(result['businessComplete'])

    def test_disappeared_or_unreviewed_command_never_runs(self):
        m=self.module()
        with patch('subprocess.run',return_value=subprocess.CompletedProcess([],0,'[]','')) as run:
            bridge=m.VicinaeBridge('/fake/cli')
            for id_ in ['files:search','power:power-off']:
                with self.assertRaises(ValueError):bridge.launch(id_,'')
            self.assertFalse(any('launch' in x.args[0] for x in run.call_args_list))

    def test_timeout_is_unknown_not_retry(self):
        m=self.module();calls=[]
        def run(argv,**kw):
            calls.append(argv)
            if 'launch' in argv:raise subprocess.TimeoutExpired(argv,5)
            return subprocess.CompletedProcess(argv,0,'[{"id":"files:search","name":"文件"}]','')
        with patch('subprocess.run',side_effect=run):
            result=m.VicinaeBridge('/fake/cli').launch('files:search','')
        self.assertEqual(result['status'],'outcome_unknown')
        self.assertEqual(sum('launch' in x for x in calls),1)

    def test_desktop_handoff_cannot_feed_generated_workflow(self):
        from backend.runtime.bubbles import validate_canvas
        from backend.runtime.protocol import Fault
        content={'bubbles':[{'id':'v','kind':'action','resource':{'action':'desktop','command':'files:search'}},{'id':'w','kind':'action','resource':{'action':'write'}}], 'groups':[]}
        # Standalone handoff is valid; it cannot masquerade as a data producer.
        validate_canvas(content)
        content['groups']=[{'id':'g','members':['v','w'],'operation':'combine'}]
        with self.assertRaises(Fault):validate_canvas(content)

class VicinaeRuntimeTests(unittest.TestCase):
    def test_launch_requires_grant_and_command_identity_prevents_duplicate_dispatch(self):
        import time
        from backend.vicinae import install_vicinae
        from backend.store import Store
        from backend.runtime import Kernel
        from backend.runtime.protocol import Fault, message
        class Bridge:
            def __init__(self):self.calls=[]
            def launch(self,command,query):
                self.calls.append((command,query));return {'status':'handed_off','businessComplete':False}
        with tempfile.TemporaryDirectory() as tmp:
            kernel=Kernel(Store(Path(tmp)/'db.sqlite'));bridge=Bridge();install_vicinae(kernel,bridge)
            try:
                def call(kind,payload,intent=None):return kernel.execute(message('command',kind,payload,'renderer',intent))
                iid=call('intent.create',{'title':'desktop test'})['value']['id']
                command=message('command','capability.run',{'capability':'vicinae.launch','input':{'command':'files:search','query':'report'}},'renderer',iid)
                with self.assertRaises(Fault):kernel.execute(command)
                self.assertEqual(bridge.calls,[])
                call('grant.create',{'capabilities':['vicinae.launch'],'expiresIn':60,'maxCalls':2,'network':False,'maxEffect':'L1','reason':'test'},iid)
                command=message('command','capability.run',command['payload'],'renderer',iid)
                a=kernel.execute(command)['task'];b=kernel.execute(command)['task'];self.assertEqual(a['id'],b['id'])
                for _ in range(100):
                    task=kernel.db.get(a['id'],'task')
                    if task['status'] not in ('running','queued'):break
                    time.sleep(.01)
                self.assertEqual(task['status'],'success');self.assertEqual(bridge.calls,[('files:search','report')])
                self.assertFalse(task['result']['businessComplete'])
            finally:kernel.shutdown()
