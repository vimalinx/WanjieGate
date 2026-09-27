import json
import threading
import time
import unittest
from backend.live_runtime import LiveRuntime, parse_scene
from backend.composition import compose
from backend.market import parse_tencent, parse_yahoo

class Generator:
    model='test-model'
    def __init__(self):self.calls=[];self.gate=None;self.entered=threading.Event();self.fail=False
    def generate(self,text,purpose,call_id):
        self.calls.append(text);self.entered.set()
        if self.gate:self.gate.wait(3)
        if self.fail:raise RuntimeError('unknown outcome')
        return json.dumps({'title':'阅读安排','blocks':[{'type':'tasks','title':'两小时安排','items':['阅读45分钟并标记重点','休息10分钟','完成写作初稿']}]}), {'model':self.model}
class Market:
    def __init__(self):self.calls=[]
    def scene(self,text):self.calls.append(text);return {'title':'行情','blocks':[{'type':'quotes','items':[{'name':'真实适配器测试值','price':25}]}]}
class LiveTests(unittest.TestCase):
    def setUp(self):self.gen=Generator();self.market=Market();self.runtime=LiveRuntime(self.gen,self.market);self.client='a'*32
    def tearDown(self):
        if self.gen.gate:self.gen.gate.set()
        self.runtime.shutdown()
    def request(self,rev,text='安排阅读计划',score=0,local=False):return self.runtime.request(self.client,rev,text,compose(text),None,{},score,local)
    def wait(self,rev):
        for _ in range(300):
            result=self.runtime.snapshot(self.client,rev)
            if result['status']!='loading':return result
            time.sleep(.01)
        self.fail('live scene did not finish')
    def test_market_runs_without_cloud_or_submit(self):
        self.request(1,'股票咋样了？',.95)
        result=self.wait(1)
        self.assertEqual(result['blocks'][0]['type'],'quotes');self.assertEqual(self.market.calls,['股票咋样了？']);self.assertEqual(self.gen.calls,[])
    def test_auto_generation_returns_content(self):
        self.request(1);self.request(1)
        result=self.wait(1)
        self.assertEqual(result['blocks'][0]['items'][0],'阅读45分钟并标记重点');self.assertEqual(len(self.gen.calls),1)
    def test_latest_replaces_pending_and_old_result(self):
        self.gen.gate=threading.Event();self.request(1,'旧的计划');self.assertTrue(self.gen.entered.wait(1))
        self.request(2,'中间计划');self.request(3,'最新计划');self.gen.gate.set();self.wait(3)
        self.assertEqual(len(self.gen.calls),2);self.assertIn('最新计划',self.gen.calls[-1]);self.assertEqual(self.runtime.snapshot(self.client,1)['status'],'superseded')
    def test_clear_cancels_pending(self):
        self.gen.gate=threading.Event();self.request(1);self.assertTrue(self.gen.entered.wait(1));self.request(2,'新计划');self.runtime.cancel(self.client,3);self.gen.gate.set()
        self.runtime.shutdown();self.assertEqual(len(self.gen.calls),1);self.assertEqual(self.runtime.snapshot(self.client,3)['status'],'idle')
    def test_local_only_never_fetches_or_generates(self):
        self.request(1,'股票咋样了？',.95,True);self.assertEqual(self.gen.calls,[]);self.assertEqual(self.market.calls,[])
    def test_failure_not_replayed_for_same_input(self):
        self.gen.fail=True;self.request(1);self.assertEqual(self.wait(1)['status'],'failed');self.request(2);self.assertEqual(self.wait(2)['status'],'failed');self.assertEqual(len(self.gen.calls),1)
    def test_schema_rejects_executable_or_malformed_blocks(self):
        for obj in [{'blocks':[{'type':'html','text':'<script>evil</script>'}]},{'blocks':[{'type':'tasks','items':'wrong'}]},{'blocks':[]}]:
            with self.assertRaises(ValueError):parse_scene(json.dumps(obj))
    def test_market_parser_requires_source_time(self):
        fields=['']*35;fields[1]='上证指数';fields[3]='25';fields[4]='20';fields[30]='20260924150000';fields[31]='5';fields[32]='25'
        q=parse_tencent('v_sh000001="'+'~'.join(fields)+'";')[0];self.assertEqual(q['price'],25);self.assertTrue(q['asof'].endswith('+08:00'))
        fields[3]='nan'
        with self.assertRaises(ValueError):parse_tencent('v_sh000001="'+'~'.join(fields)+'";')

if __name__=='__main__':unittest.main()
