"""HTTP transport tests against an isolated runtime; no upstream calls."""
import json
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from backend.server import create_server
from backend.runtime.protocol import message

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=create_server(0,self.tmp.name)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.server.kernel.shutdown();self.tmp.cleanup()
    def request(self,path,body=None,headers=None):
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**(headers or {})})
        try:
            with urllib.request.urlopen(req) as r:return r.status,json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:return e.code,json.loads(e.read())
    def command(self,type_,payload=None,intent=None,**kw):
        return self.request('/api/runtime/commands',message('command',type_,payload or {},'renderer',intent,**kw))
    def intent(self):return self.command('intent.create',{'title':'HTTP 验收'})[1]['value']['id']
    def test_browser_route_and_persistent_note(self):
        i=self.intent();code,result=self.command('artifact.create',{'kind':'note','title':'笔记','content':{'text':'保留'}},i)
        self.assertEqual(code,200);a=result['value'];state=self.request('/api/runtime/intents/'+i)[1]
        self.assertEqual(state['artifacts'][0]['id'],a['id'])
        with urllib.request.urlopen(self.base+'/w/'+i) as r:self.assertIn('runtime-app.js',r.read().decode())
    def test_cross_origin_and_host(self):
        c=message('command','intent.create',{'title':'bad'},'renderer')
        self.assertEqual(self.request('/api/runtime/commands',c,{'Origin':'https://untrusted.example'})[0],403)
        self.assertEqual(self.request('/api/runtime/state',headers={'Host':'untrusted.example'})[0],403)
    def test_legacy_write_and_forged_signal_rejected(self):
        self.assertEqual(self.request('/api/workspaces',{})[1]['code'],'legacy_read_only')
        forged=message('signal','intent.phase',{},'kernel')
        self.assertEqual(self.request('/api/runtime/commands',forged)[0],400)
    def test_cursor_and_schema(self):
        i=self.intent();self.command('intent.activate',intent=i)
        events=self.request('/api/runtime/messages/0/'+i)[1];self.assertTrue(events['messages'])
        self.assertEqual(self.request('/api/runtime/messages/'+str(events['cursor'])+'/'+i)[1]['messages'],[])
        self.assertEqual(self.request('/api/runtime/schema/message')[1]['properties']['protocolVersion']['const'],'0.1')
    def test_invalid_import_has_failed_task_no_artifact(self):
        i=self.intent();code,r=self.command('capability.run',{'capability':'data.import','input':{'text':'invalid'}},i)
        self.assertEqual(code,200)
        for _ in range(100):
            state=self.request('/api/runtime/intents/'+i)[1]
            if state['tasks'][0]['status'] not in ('queued','running'):break
            time.sleep(.01)
        self.assertEqual(state['tasks'][0]['status'],'failure');self.assertEqual(state['artifacts'],[])
    def test_denial_and_revision_http_codes(self):
        i=self.intent();code,r=self.command('capability.run',{'capability':'text.generate','input':{'text':'write'}},i)
        self.assertEqual(code,403);self.assertEqual(r['code'],'local_only')
        self.assertEqual(self.command('intent.update',{'title':'stale'},i,expectedRevision=100)[0],409)
        self.assertEqual(self.server.kernel.db.list('task'),[])

if __name__=='__main__':unittest.main()
