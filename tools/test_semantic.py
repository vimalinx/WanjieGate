"""OpenRouter contract regression. Every transport is mocked; no paid calls."""
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch, Mock
from backend.runtime.semantic import OpenRouterSemantic, PHASES, request_body, signals_from
from backend.runtime.protocol import Fault
from backend.providers import ProviderError

CONTEXT={'intentState':{'goal':'build runtime'},'items':[]}
def response_for(body):
    answers={}
    defaults={'relation':'CONTINUE','operation':'MODIFY','phase':'ACT','attention':'FOREGROUND','commitment':'READY','thread':'NONE','target':'NONE'}
    for k,q in body['questions'].items():
        if q['type']=='noul':answers[k]={'type':'noul','noul':.1 if k=='compound' else .9}
        else:
            chosen=defaults.get(k.split('_')[-1],next(iter(q['criteria'])))
            answers[k]={'type':'choice','choice':chosen,'confidence':.99,'probabilities':{p:1 if p==chosen else 0 for p in q['criteria']}}
    return {'answers':answers,'model':'typesafe/jev-1.13-20260917','id':'test-receipt','usage':{'cost':.00003}}

class SemanticTests(unittest.TestCase):
    def test_typed_answers_and_model_identity(self):
        body=request_body('fix bug',CONTEXT,'typesafe/jev-1.13');data=response_for(body)
        self.assertEqual(signals_from(data,body)[0]['value']['phase'],'ACT')
        data['answers']['compound']['noul']=True
        with self.assertRaises(ValueError):signals_from(data,body)
        data=response_for(body);data['model']='other/model'
        with self.assertRaises(ValueError):signals_from(data,body)
        data=response_for(body);del data['answers']['s0_phase']['probabilities']['EXPLORE']
        with self.assertRaises(ValueError):signals_from(data,body)
    def test_context_obeys_selected_projection(self):
        ctx={**CONTEXT,'items':[{'artifact':'a','title':'note','kind':'note','version':3,'detail':'metadata','content':{'title':'note'},'source':'user'}]}
        body=request_body('find note',ctx,'typesafe/jev-1.13')
        self.assertEqual(body['state']['artifacts'][0]['content'],{'title':'note'})
    def test_success_receipt_never_contains_credential(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'OPENROUTER_API_KEY':'unit-test-secret'}),patch('urllib.request.build_opener') as opener:
            transport=opener.return_value.open.return_value.__enter__.return_value
            transport.status=200;transport.read.return_value=json.dumps(response_for(request_body('fix',CONTEXT,'typesafe/jev-1.13'))).encode()
            p=OpenRouterSemantic(root);result=p.observe('fix',CONTEXT)
            self.assertEqual(result['semantic']['state'],'ready');self.assertIn('latencyMs',result['semantic'])
            opener.return_value.open.assert_called_once()
            for f in Path(root).rglob('*'):
                if f.is_file():
                    self.assertEqual(f.stat().st_mode & 0o777,0o600)
                    self.assertNotIn('unit-test-secret',f.read_text())
    def test_http_rejection_and_transport_unknown_never_retry(self):
        for failure in (urllib.error.HTTPError('https://openrouter.ai',429,'limited',{},None),urllib.error.URLError('timeout')):
            with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'OPENROUTER_API_KEY':'unit-test-secret'}),patch('urllib.request.build_opener') as opener:
                opener.return_value.open.side_effect=failure;p=OpenRouterSemantic(root)
                with self.assertRaises((Fault,ProviderError)):p.observe('fix',CONTEXT)
                opener.return_value.open.assert_called_once()
                self.assertEqual(p.last['state'],'rejected' if isinstance(failure,urllib.error.HTTPError) else 'outcome_unknown')
    def test_missing_key_stops_before_network(self):
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'OPENROUTER_API_KEY':''}),patch('urllib.request.build_opener') as opener:
            with self.assertRaises(Fault):OpenRouterSemantic(root).observe('fix',CONTEXT)
            opener.assert_not_called()

if __name__=='__main__':unittest.main()
