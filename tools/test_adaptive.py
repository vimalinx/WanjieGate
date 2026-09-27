"""Adaptive surfaces: real contracts, isolated transport and persistent ownership."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from backend.runtime.presentation import query_candidates,interpret
from backend.runtime.semantic import request_body
from backend.runtime.references import web_search
from backend.runtime.protocol import Fault
from tools.test_semantic import response_for,CONTEXT
from tools import test_runtime

class AdaptiveTests(unittest.TestCase):
    setUp=test_runtime.RuntimeTests.setUp
    tearDown=test_runtime.RuntimeTests.tearDown
    call=test_runtime.RuntimeTests.call
    command=test_runtime.RuntimeTests.command
    artifact=test_runtime.RuntimeTests.artifact
    wait=test_runtime.RuntimeTests.wait
    def test_surface_candidates_are_bounded_and_model_output_validated(self):
        self.assertEqual(query_candidates('我想写一篇关于间隔重复的笔记，需要案例')[0],'间隔重复')
        body=request_body('直接开始写我的日记。',CONTEXT,'typesafe/jev-1.13');data=response_for(body);data['answers']['support_editor']['noul']=.9
        self.assertEqual(interpret(data,body)['editor'],.9)
        data['answers']['support_editor']['noul']=float('nan')
        with self.assertRaises(ValueError):interpret(data,body)
    def test_persistent_layout_and_document_identity(self):
        a=self.artifact(kind='note',content={'text':'不丢的正文'})
        self.call('surface.update',{'mode':'writing','document':a['id'],'blocks':{'references':{'lane':'left','order':0,'pinned':True}}})
        snap=self.kernel.snapshot(self.intent)
        self.assertEqual(snap['surface']['document'],a['id'])
        self.assertEqual(snap['surface']['blocks']['references']['lane'],'left')
        self.call('surface.update',{'mode':'market'})
        self.assertEqual(self.kernel.snapshot(self.intent)['surface']['document'],a['id'])
        self.assertEqual(self.kernel.db.get(a['id'])['content']['text'],'不丢的正文')
    def test_surface_cannot_take_another_intent_document(self):
        original=self.intent;a=self.artifact()
        self.intent=self.call('intent.create',{'title':'other'})['value']['id']
        with self.assertRaises(Fault):self.call('surface.update',{'document':a['id'],'mode':'writing'})
        self.intent=original
    def test_image_pixels_do_not_enter_semantic_context(self):
        a=self.artifact(kind='image',content={'data':'data:image/jpeg;base64,YWJj','description':'本地截图'})
        ctx=self.kernel.snapshot(self.intent)['context']
        item=next(i for i in ctx['items'] if i['artifact']==a['id'])
        self.assertEqual(item['detail'],'metadata');self.assertNotIn('YWJj',json.dumps(item))
        task=self.wait(self.call('semantic.observe',{'text':'写笔记'})['task'])
        self.assertEqual(task['status'],'success')
        self.assertEqual(self.kernel.db.get(self.intent)['state']['phase'],'researching')
    def test_local_only_blocks_reference_search(self):
        with self.assertRaises(Fault):self.call('capability.run',{'capability':'reference.search','input':{'query':'learning'}})
    def test_search_receipts_and_provenance(self):
        def run(args,stdout,**kw):
            stdout.write(json.dumps({'credits_charged':.6,'data':{'web':{'results':[{'title':'Example','url':'https://example.org/case','description':'A <strong>real</strong> snippet'},{'title':'bad','url':'javascript:alert(1)','description':'no'}]}}}))
            stdout.flush();return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as root,patch('subprocess.run',side_effect=run) as invoke:
            result=web_search('case',root)
            self.assertEqual(len(result['entries']),1)
            self.assertEqual(result['entries'][0]['kind'],'search-snippet')
            self.assertEqual(result['entries'][0]['text'],'A real snippet')
            invoke.assert_called_once()
            for p in Path(root).rglob('*'):
                if p.is_file():self.assertEqual(p.stat().st_mode&0o777,0o600)
    def test_unknown_search_is_never_retried(self):
        import subprocess
        from backend.providers import ProviderError
        with tempfile.TemporaryDirectory() as root,patch('subprocess.run',side_effect=subprocess.TimeoutExpired('lr',45)) as invoke:
            with self.assertRaises(ProviderError):web_search('case',root)
            invoke.assert_called_once()

if __name__=='__main__':unittest.main()
