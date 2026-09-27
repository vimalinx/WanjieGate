"""Local HTTP integration tests. Isolated store; no upstream model calls."""
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
from backend.server import create_server

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.server=create_server(0,self.tmp.name)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.server.scheduler.pool.shutdown(); self.server.live.shutdown(); self.tmp.cleanup()
    def request(self,path,body=None,method=None,headers=None):
        hdr={'Content-Type':'application/json',**(headers or {})}
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=hdr,method=method)
        try:
            with urllib.request.urlopen(req) as r: return r.status,json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e: return e.code,json.loads(e.read())
    def test_persistence_note_export_and_route(self):
        _,w=self.request('/api/workspaces',{}); key=w['id']
        _,a=self.request(f'/api/workspaces/{key}/note',{'text':'# 本地笔记\n内容'})
        self.assertEqual(a['type'],'document')
        _,w=self.request(f'/api/workspaces/{key}'); self.assertEqual(len(w['artifacts']),1)
        _,export=self.request(f'/api/workspaces/{key}/export'); self.assertIn('本地笔记',export['text'])
        with urllib.request.urlopen(self.base+'/w/'+key) as r: self.assertIn('万界门',r.read().decode())
    def test_cross_origin_and_host_rejected(self):
        self.assertEqual(self.request('/api/workspaces',{},headers={'Origin':'https://untrusted.example'})[0],403)
        self.assertEqual(self.request('/api/workspaces',headers={'Host':'untrusted.example'})[0],403)
    def test_bad_import_no_mutation(self):
        _,w=self.request('/api/workspaces',{})
        self.assertEqual(self.request(f"/api/workspaces/{w['id']}/dataset",{'text':'not a dataset'})[0],400)
        self.assertIsNone(self.request(f"/api/workspaces/{w['id']}")[1]['dataset'])
    def test_local_only_generation_rejected(self):
        _,w=self.request('/api/workspaces',{})
        code,data=self.request(f"/api/workspaces/{w['id']}/jobs",{'text':'写文章','selected':['write'],'request_id':'unique-request-00000001','local_only':True})
        self.assertEqual(code,400)
        self.assertEqual(self.server.store.jobs(),[])

    def test_preview_without_workspace_does_not_save_history(self):
        with patch.object(self.server.kev, 'decide', return_value=({'write': .9}, {'source': 'test'})):
            code, data = self.request('/api/preview', {'text': '写一段文字', 'workspace': None})
        self.assertEqual(code, 200)
        self.assertEqual(data['steps'][0]['id'], 'write')
        self.assertEqual(self.request('/api/workspaces')[1]['workspaces'], [])
        self.assertEqual(self.server.store.jobs(), [])
        self.assertEqual(self.request('/api/preview', {'text': '写一段文字', 'workspace': 'missing'})[0], 404)

    def test_live_analysis_without_job_or_artifact(self):
        _, w = self.request('/api/workspaces', {})
        key = w['id']
        self.request(f'/api/workspaces/{key}/dataset', {'text': '日期,数量\n一,10\n二,15'})
        with patch.object(self.server.kev, 'decide', return_value=({'analyze': .95}, {'source': 'test'})):
            code, data = self.request('/api/preview', {'text': '分析数据', 'workspace': key})
        self.assertEqual(code, 200)
        self.assertEqual(data['analysis']['columns'][0]['total'], 25)
        self.assertEqual(self.request(f'/api/workspaces/{key}')[1]['artifacts'], [])
        self.assertEqual(self.server.store.jobs(), [])

if __name__=='__main__': unittest.main()
