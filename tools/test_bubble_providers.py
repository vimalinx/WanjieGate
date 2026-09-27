import io
import json
import unittest
from unittest.mock import patch
from backend.bubble_providers import JevClient, OpenRouterGenerator, BubbleProviderError

class ProviderTests(unittest.TestCase):
    def test_decisions_shape(self):
        seen=[]
        def respond(req, **kw):
            seen.append((req.full_url,json.loads(req.data)))
            return io.BytesIO(json.dumps({'model':'typesafe/jev-1.13','answers':{'route':{'type':'choice','choice':'yes','probabilities':{'yes':.9,'none':.1},'confidence':.5}}}).encode())
        with patch('urllib.request.urlopen',respond):
            result=JevClient({'OPENROUTER_API_KEY':'secret'}).decide({'text':'写作'},{'route':{'type':'choice','instructions':'选一个','criteria':{'yes':'写作','none':'无匹配'}}})
        self.assertEqual(seen[0][0],'https://openrouter.ai/api/alpha/decisions')
        self.assertEqual(seen[0][1]['state'],{'text':'写作'})
        self.assertEqual(result['answers']['route']['choice'],'yes')
    def test_invalid_answers_fail(self):
        for answer in [{}, {'x':{'type':'noul','noul':float('nan')}}, {'x':{'type':'choice','choice':'bad','probabilities':{'ok':1},'confidence':1}}]:
            with self.subTest(answer=answer),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps({'answers':answer}).encode())):
                with self.assertRaises(BubbleProviderError):
                    JevClient({'OPENROUTER_API_KEY':'secret'}).decide({}, {'x':{'type':'choice','criteria':{'ok':'OK'}}})
    def test_key_never_in_error(self):
        with patch('urllib.request.urlopen',side_effect=OSError('secret')):
            with self.assertRaises(BubbleProviderError) as err: JevClient({'OPENROUTER_API_KEY':'secret'}).decide({}, {})
            self.assertNotIn('secret',str(err.exception))
    def test_generation_failure_not_retried(self):
        with patch('urllib.request.urlopen',side_effect=TimeoutError()) as request:
            with self.assertRaises(BubbleProviderError):OpenRouterGenerator({'OPENROUTER_API_KEY':'secret'}).generate('x','y','id')
            self.assertEqual(request.call_count,1)
    def test_truncated_generation_fails(self):
        with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps({'choices':[{'finish_reason':'length','message':{'content':'partial'}}]}).encode())):
            with self.assertRaises(BubbleProviderError):OpenRouterGenerator({'OPENROUTER_API_KEY':'secret'}).generate('x','y','id')

if __name__=='__main__':unittest.main()
