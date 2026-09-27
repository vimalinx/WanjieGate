import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from backend.store import Store
from backend.runtime import Kernel
from backend.runtime.protocol import Fault,message
from backend.runtime.bubbles import install_bubbles,validate_canvas,freeze_sources,validate_citations

class Gen:
    model='controlled';last={}
    def __init__(self):self.prompts=[];self.gate=None;self.entered=threading.Event()
    def generate(self,prompt,purpose,key):
        self.prompts.append(json.loads(prompt));self.entered.set()
        if self.gate:self.gate.wait(3)
        return '依据资料形成的内容 [1]',{'model':self.model}
class Jev:
    def decide(self,state,questions):
        return {'answers':{k:({'type':'noul','noul':.9} if q['type']=='noul' else {'type':'choice','choice':next(iter(q['criteria'])),'confidence':1,'probabilities':{v:1 if i==0 else 0 for i,v in enumerate(q['criteria'])}}) for k,q in questions.items()},'model':'controlled','elapsed_ms':1}

class BubbleRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.gen=Gen();self.k=Kernel(Store(Path(self.tmp.name)/'test.sqlite'),self.gen)
        install_bubbles(self.k,Jev(),self.gen)
        self.intent=self.call('intent.create',{'title':'bubble test'})['value']['id']
        self.call('intent.update',{'preferences':{'localOnly':False}})
        self.call('grant.create',{'capabilities':['bubble.execute','text.generate','web.read','market.query','bubble.merge','bubble.suggest'],'expiresIn':3600,'maxCalls':100,'network':True,'maxEffect':'L2','reason':'test'})
    def tearDown(self):
        if self.gen.gate:self.gen.gate.set()
        self.k.shutdown();self.tmp.cleanup()
    def call(self,t,p):return self.k.execute(message('command',t,p,'renderer',getattr(self,'intent',None)))
    def source(self,text):return self.call('artifact.create',{'kind':'note','title':text[:100],'content':{'text':text},'source':'fixture'})['value']
    def canvas(self):
        a=self.source('first evidence');b=self.source('second evidence');self.source('UNSELECTED SECRET')
        content={'input':'写作','inputRevision':1,'positions':{},'bubbles':[{'id':a['id'],'kind':'source','title':a['title'],'resource':{'artifact':a['id'],'version':a['version'],'detail':'full'}},{'id':b['id'],'kind':'source','title':b['title'],'resource':{'artifact':b['id'],'version':b['version'],'detail':'full'}},{'id':'write','kind':'action','title':'写作','resource':{'action':'write'}}],'groups':[{'id':'group','version':0,'members':[a['id'],b['id'],'write'],'operation':'combine'}]}
        return self.call('artifact.create',{'kind':'bubble-canvas','title':'画布','content':content})['value']
    def run_cmd(self,c,runid='run-1'):
        cmd=message('command','bubble.run',{'runId':runid,'canvas':c['id'],'version':c['version'],'groupId':'group','text':'根据资料写作'},'renderer',self.intent);cmd['id']=runid;cmd['idempotencyKey']=runid;return cmd
    def wait(self,t):
        for _ in range(400):
            task=self.k.db.get(t['id'],'task')
            if task['status'] not in ('queued','running'):return task
            time.sleep(.01)
        self.fail('timeout')
    def test_canvas_roundtrip_and_version_conflict(self):
        c=self.canvas();self.assertEqual(len(self.k.db.get(c['id'])['content']['bubbles']),3)
        self.call('artifact.update',{'artifact':c['id'],'version':0,'title':'changed'})
        with self.assertRaises(Fault):self.call('artifact.update',{'artifact':c['id'],'version':0,'title':'stale'})
    def test_run_dedup_and_payload_conflict(self):
        c=self.canvas();cmd=self.run_cmd(c);a=self.k.execute(cmd)['task'];b=self.k.execute(cmd)['task'];self.assertEqual(a['id'],b['id'])
        cmd['payload']['text']='changed'
        with self.assertRaises(Fault):self.k.execute(cmd)
    def test_two_selected_sources_reach_generator(self):
        c=self.canvas();t=self.wait(self.k.execute(self.run_cmd(c))['task']);self.assertEqual(t['status'],'success',t.get('error'))
        raw=json.dumps(self.gen.prompts);self.assertIn('first evidence',raw);self.assertIn('second evidence',raw);self.assertNotIn('UNSELECTED SECRET',raw)
    def test_run_snapshot_survives_canvas_edit(self):
        c=self.canvas();self.gen.gate=threading.Event();t=self.k.execute(self.run_cmd(c))['task'];self.assertTrue(self.gen.entered.wait(2))
        self.call('artifact.update',{'artifact':c['id'],'version':0,'content':{'input':'','inputRevision':2,'bubbles':[],'groups':[],'positions':{}}})
        self.gen.gate.set();self.assertEqual(self.wait(t)['status'],'success');self.assertEqual(len(self.gen.prompts[0]['sources']),2)
    def test_selected_version_and_budget_checked(self):
        a=self.source('x'*500)
        with self.k.db.transaction() as tx:
            for ref,budget in [({'artifact':a['id'],'version':99,'detail':'full'},12000),({'artifact':a['id'],'version':0,'detail':'full'},200),({'artifact':a['id'],'version':0,'detail':'metadata'},12000)]:
                with self.assertRaises(Fault):freeze_sources(tx,self.intent,[ref],budget)
    def test_unknown_citation_fails(self):
        with self.assertRaises(Fault):validate_citations('内容 [99]',[{'title':'a'}])
    def test_cycle_and_step_limit(self):
        with self.assertRaises(Fault):validate_canvas({'bubbles':[],'groups':[{'id':'g','members':['g'],'operation':'combine','version':0}],'positions':{}})
    def test_user_negation_blocks_run(self):
        c=self.canvas();cmd=self.run_cmd(c);cmd['payload']['text']='不要代写正文'
        with self.assertRaises(Fault):self.k.execute(cmd)

if __name__=='__main__':unittest.main()
