"""v0.2 offline contracts and execution boundaries; no provider calls."""
import copy
import threading
import unittest
from backend.runtime.control import candidates, compose, contract, STAGES
from backend.runtime.semantic import request_body, interpret
from backend.runtime.protocol import Fault, validate
from tools.test_semantic import response_for
from tools import test_runtime

class ControlTests(unittest.TestCase):
    setUp=test_runtime.RuntimeTests.setUp
    tearDown=test_runtime.RuntimeTests.tearDown
    call=test_runtime.RuntimeTests.call
    command=test_runtime.RuntimeTests.command
    wait=test_runtime.RuntimeTests.wait
    artifact=test_runtime.RuntimeTests.artifact
    def frame_output(self,text='查文档，顺便晚上充电',event=None):
        ctx={'intent':self.intent,'revision':self.kernel.db.get(self.intent)['version'],'intentState':{'goal':'完成协议'},'items':[]}
        if event:ctx['event']=event
        body=request_body(text,ctx,'typesafe/jev-1.13');data=response_for(body)
        for k in list(data['answers']):
            if k.endswith('_operation'):
                a=data['answers'][k];a.update(choice='RETRIEVE',probabilities={p:int(p=='RETRIEVE') for p in a['probabilities']})
        return interpret(data,body,ctx)
    def test_compound_one_snapshot_and_no_semantic_commit(self):
        signals,run=self.frame_output()
        self.assertEqual(len(run['frames']),2)
        self.assertEqual([n['stage'] for n in run['nodes']],STAGES)
        for node in run['nodes']:validate(node,contract('node-'+node['stage'].lower()))
        self.assertEqual(run['nodes'][6]['status'],'waiting')
        self.assertTrue(all(f['commitment']!='COMMITTED' for f in run['frames']))
        self.assertEqual(len(self.kernel.db.list('intent')),1)
    def test_partial_cannot_claim_ready(self):
        _,run=self.frame_output('查文档',{'type':'asr.partial','source':'test','text':'查文档','final':False})
        self.assertEqual(run['frames'][0]['commitment'],'HYPOTHESIS')
    def test_selected_candidate_precedes_limit(self):
        targets=[{'artifact':str(i),'tier':'HOT'} for i in range(20)]
        self.assertEqual(candidates({'targetCandidates':targets,'selectedArtifact':'19'})['targets'][0]['artifact'],'19')
    def test_stream_order_rejects_stale_input(self):
        e={'type':'asr.partial','source':'test','text':'查','final':False,'stream':'s','sequence':2}
        self.call('event.observe',{'event':e})
        with self.assertRaises(Fault):self.call('event.observe',{'event':{**e,'sequence':1}})
    def test_new_partial_invalidates_inflight_signal(self):
        self.semantic.gate=threading.Event()
        e={'type':'asr.partial','source':'test','text':'查','final':False,'stream':'s','sequence':1}
        task=self.call('event.observe',{'event':e,'analyze':True})['task']
        self.assertTrue(self.semantic.entered.wait(2))
        self.call('event.observe',{'event':{**e,'sequence':2,'text':'查代码'}})
        self.semantic.gate.set();self.wait(task)
        self.assertNotEqual(self.kernel.db.get(self.intent)['state']['phase'],'researching')
    def test_closed_is_retained_and_restorable(self):
        a=self.artifact()
        self.call('intent.transition',{'lifecycle':'CLOSED'})
        self.assertEqual(self.kernel.db.get(a['id'])['intent'],self.intent)
        self.call('intent.transition',{'lifecycle':'FOREGROUND'})
        self.assertEqual(self.kernel.snapshot()['activeIntent'],self.intent)
        self.call('intent.transition',{'lifecycle':'BACKGROUND'})
        self.call('intent.update',{'title':'后台工作'})
        self.assertEqual(self.kernel.db.get(self.intent)['lifecycle'],'BACKGROUND')
    def test_explicit_frame_commit_and_output_verification(self):
        _,run=self.frame_output('查文档');frame=run['frames'][0]
        with self.kernel.db.transaction() as tx:tx.put(frame,create=True)
        task=self.wait(self.call('frame.commit',{'frame':frame['id'],'capability':'data.import','input':{'text':'a,b\nx,1\ny,2'}})['task'])
        self.assertEqual(task['status'],'success')
        self.assertEqual(task['verification']['goalCompletion'],'unknown')
        self.assertEqual(self.kernel.db.get(frame['id'])['commitment'],'COMMITTED')
        validate(self.kernel.db.get(frame['id']),contract('intent-frame'))
        with self.assertRaises(Fault):self.call('frame.commit',{'frame':frame['id'],'capability':'data.import','input':{'text':'a,b\nx,1\ny,2'}})
    def test_notification_urgency_is_independent_of_relevance(self):
        n=self.call('notification.receive',{'title':'提醒','text':'提醒内容'})['value']
        for relevant,urgent,expected in ((True,False,'attached'),(False,True,'interrupt')):
            self.semantic.observe=lambda text,ctx:{'artifacts':[],'signals':[{'name':'notification.relevance','score':.99,'model':'test','value':{'notification':n['id'],'relevant':relevant,'urgent':urgent,'interruptible':True}}]}
            self.wait(self.call('semantic.observe',{'text':'通知判断'})['task'])
            self.assertEqual(self.kernel.db.get(n['id'])['status'],expected)
    def test_new_observation_invalidates_accepted_frame(self):
        _,run=self.frame_output('查文档');frame=run['frames'][0];frame['acceptedInput']='old'
        with self.kernel.db.transaction() as tx:
            tx.put(frame,create=True);tx.set_meta('control.input:'+self.intent,'old')
        self.call('event.observe',{'event':{'type':'asr.partial','source':'test','text':'新要求','final':False}})
        with self.assertRaises(Fault):self.call('frame.commit',{'frame':frame['id'],'capability':'data.import','input':{'text':'a,b\nx,1\ny,2'}})
    def test_frame_invalidated_by_explicit_state_change(self):
        _,run=self.frame_output('查文档');frame=run['frames'][0]
        with self.kernel.db.transaction() as tx:tx.put(frame,create=True)
        self.call('intent.update',{'title':'changed'})
        with self.assertRaises(Fault):self.call('frame.commit',{'frame':frame['id'],'capability':'data.import','input':{'text':'a,b\nx,1\ny,2'}})

if __name__=='__main__':unittest.main()
