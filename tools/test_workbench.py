#!/usr/bin/env python3
"""Offline contract tests; never call a real provider or touch user workspaces."""
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from backend.composition import compose, parse_dataset, analyze
from backend.store import Store
from backend.scheduler import Scheduler, TERMINAL
from backend.providers import ProviderError

CSV = '日期,销售额,订单\n周一,10,2\n周二,20,4\n周三,30,6'

class FakeGenerator:
    model = 'test-only'
    def __init__(self):
        self.calls = []
        self.gate = None
        self.entered = threading.Event()
        self.fail = False
    def generate(self, prompt, purpose, key):
        self.calls.append((prompt,purpose,key)); self.entered.set()
        if self.gate: self.gate.wait(4)
        if self.fail: raise ProviderError('provider unavailable')
        return ('[{"title":"检查转化","detail":"比较各日订单"}]' if key.endswith('-plan') else '# 周报\n销售合计60。'), {'receipt':key}

class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name)/'db.sqlite3')
        self.gen = FakeGenerator()
        self.scheduler = Scheduler(self.store,self.gen)
        self.w = self.store.new_workspace()
        self.store.mutate(self.w['id'], lambda w:w.update(dataset=parse_dataset(CSV)))
    def tearDown(self):
        if self.gen.gate: self.gen.gate.set()
        self.scheduler.pool.shutdown(wait=True)
        self.tmp.cleanup()
    def wait(self, job):
        end = time.monotonic()+5
        while time.monotonic()<end:
            j=self.store.job(job['id'])
            if j['status'] in TERMINAL: return j
            time.sleep(.01)
        self.fail('job did not finish')
    def submit(self, selected=None, key='request-00000000001'):
        return self.scheduler.submit(self.w['id'],'分析数据，写周报，制定行动计划',selected,key)
    def test_compound_is_not_ambiguity(self):
        p=compose('分析数据，写周报，制定行动计划',parse_dataset(CSV),scores={'analyze':.9,'write':.94,'plan':.93})
        self.assertEqual([s['id'] for s in p['steps']],['analyze','write','plan'])
        self.assertEqual(p['steps'][2]['depends'],['analyze','write'])
    def test_kev_can_reject_negated_keyword(self):
        p=compose('不要分析数据，只写文字',scores={'analyze':.02,'write':.95,'plan':.02,'answer':.1})
        self.assertEqual([s['id'] for s in p['steps']],['write'])
        self.assertFalse(p['needs_data'])
    def test_absent_data_is_blocked(self):
        self.assertTrue(compose('分析数据')['needs_data'])
    def test_numeric_integrity(self):
        a=analyze(parse_dataset(CSV)); self.assertEqual(a['columns'][0]['total'],60)
        self.assertEqual(a['columns'][0]['change'],200)
        for raw in ['x,y\na,nan\nb,inf','x,y\na,1\nb,2,3','x,x\na,1\nb,2']:
            with self.assertRaises(ValueError): parse_dataset(raw)
    def test_graph_results_and_context(self):
        j=self.wait(self.submit()); self.assertEqual(j['status'],'complete')
        w=self.store.workspace(self.w['id']); self.assertEqual([a['type'] for a in w['artifacts']],['analysis','document','tasks'])
        self.assertIn('statistics',self.gen.calls[0][0]); self.assertIn('current_document',self.gen.calls[1][0])
        self.assertEqual(len(self.gen.calls),2)
    def test_idempotency(self):
        j=self.submit(); same=self.submit(); self.assertEqual(j['id'],same['id'])
        self.wait(j); self.assertEqual(len(self.gen.calls),2)
        with self.assertRaises(ValueError): self.scheduler.submit(self.w['id'],'different',['write'],'request-00000000001')
    def test_cancel_no_downstream_or_writeback(self):
        self.gen.gate=threading.Event(); j=self.submit(); self.assertTrue(self.gen.entered.wait(2))
        self.scheduler.cancel(j['id']); self.gen.gate.set(); j=self.wait(j)
        self.assertEqual(j['status'],'cancelled'); self.assertEqual(len(self.gen.calls),1)
        self.assertEqual(len(self.store.workspace(self.w['id'])['artifacts']),1)
    def test_provider_failure_preserves_analysis(self):
        self.gen.fail=True; j=self.wait(self.submit()); self.assertEqual(j['status'],'failed')
        self.assertEqual(len(self.gen.calls),1); self.assertEqual(len(self.store.workspace(self.w['id'])['artifacts']),1)
    def test_local_mode_never_calls_model(self):
        with self.assertRaises(ValueError): self.scheduler.submit(self.w['id'],'写文章',['write'],'request-00000000002',True)
        self.assertFalse(self.gen.calls)
    def test_requested_task_count(self):
        self.gen.generate = lambda prompt, purpose, key: (json.dumps([{'title':f'行动{i}','detail':'可验证的完成标准'} for i in range(6)]), {'receipt':key})
        j=self.scheduler.submit(self.w['id'],'列出3条可执行的行动计划',['plan'],'request-task-count-0001')
        self.assertEqual(self.wait(j)['status'],'complete')
        self.assertEqual(len(self.store.workspace(self.w['id'])['artifacts'][0]['data']['items']),3)
    def test_edit_conflict_and_persistence(self):
        self.wait(self.submit(['write']))
        a=self.store.workspace(self.w['id'])['artifacts'][0]
        self.store.edit_artifact(self.w['id'],a['id'],{'version':0,'text':'修改后','pinned':True})
        with self.assertRaises(ValueError): self.store.edit_artifact(self.w['id'],a['id'],{'version':0,'text':'stale'})
        recovered=Store(self.store.path).workspace(self.w['id'])['artifacts'][0]
        self.assertEqual(recovered['data']['text'],'修改后'); self.assertTrue(recovered['pinned'])
    def test_restart_does_not_replay(self):
        job={'id':'old','workspace':self.w['id'],'request_id':'old-request','status':'running','created':time.time(),'events':[]}
        self.store.save_job(job); other=Scheduler(self.store,self.gen)
        try: self.assertEqual(self.store.job('old')['status'],'interrupted'); self.assertFalse(self.gen.calls)
        finally: other.pool.shutdown()

if __name__=='__main__': unittest.main()
