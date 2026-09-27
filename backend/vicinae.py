"""Reviewed Vicinae entrypoints, invoked through the existing task runtime."""
import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

# These open existing views. Destructive/system actions are not inferred from names.
COMMANDS = {
    'files:search': ('搜索本机文件', '查找电脑上的文档、论文和文件；打开 Vicinae 文件搜索', True),
    'clipboard:history': ('找回剪贴板内容', '查看之前复制的文字、链接与资料；打开剪贴板历史', True),
    'browser-extension:browse-tabs': ('找回浏览器标签页', '查找已打开的网页与研究资料；需要浏览器扩展连接', True),
    'calculator:history': ('查看计算记录', '打开已有计算历史，不提供股票报价', False),
    'snippets:manage': ('管理常用文案', '打开已保存的文字片段与常用文案', False),
    'wm:switch-windows': ('切换工作窗口', '找到并切换已打开的工作窗口', True),
}

class VicinaeBridge:
    def __init__(self, cli=None):
        bundle='/Applications/Vicinae.app/Contents/MacOS/vicinae-cli'
        self.cli=cli or os.environ.get('WANJIE_VICINAE_CLI') or shutil.which('vicinae') or (bundle if Path(bundle).is_file() else None)
        self._cache=None;self._at=0;self._lock=threading.Lock()

    def catalog(self, fresh=False):
        with self._lock:
            if not fresh and self._cache is not None and time.monotonic()-self._at<10:return self._cache
            if not self.cli:raise ValueError('未找到 Vicinae，请先安装并启动应用')
            try:
                p=subprocess.run([self.cli,'cmd','ls','--json'],capture_output=True,text=True,timeout=4,check=True)
                rows=json.loads(p.stdout)
                if not isinstance(rows,list) or any(not isinstance(x,dict) or not isinstance(x.get('id'),str) or not isinstance(x.get('name'),str) for x in rows):raise ValueError()
            except (OSError,ValueError,subprocess.SubprocessError):raise ValueError('无法读取 Vicinae 命令目录，请确认应用正在运行') from None
            self._cache=rows;self._at=time.monotonic();return rows

    def candidates(self,text):
        # Forward only an explicit search term. A whole natural-language request
        # is usually a bad file-name filter; leave the view ready for refinement.
        terms=re.findall(r'[“"「](.*?)[”"」]',text)
        if not terms:terms=re.findall(r'(?<![\w.])([\w-]+\.(?:pdf|md|docx|txt|pptx|xlsx|py|js|png|jpg))(?!\w)',text,re.I)
        query=terms[0] if terms else ''
        return [{'id':'vicinae:'+r['id'],'kind':'action','title':COMMANDS[r['id']][0],
                 'description':COMMANDS[r['id']][1]+'；只打开界面，不自动取得内容',
                 'resource':{'action':'desktop','command':r['id'],'query':query if COMMANDS[r['id']][2] else ''}}
                for r in self.catalog() if r['id'] in COMMANDS]

    def status(self):
        try:
            rows=self.catalog()
            return {'available':True,'loaded':len(rows),'supported':sum(r['id'] in COMMANDS for r in rows)}
        except ValueError as e:return {'available':False,'message':str(e)}

    def launch(self,command,query):
        if command not in COMMANDS:raise ValueError('这个命令尚未接入万界门')
        if not isinstance(query,str) or len(query)>1800 or '\x00' in query:raise ValueError('查询参数无效')
        if command not in {r['id'] for r in self.catalog(fresh=True)}:raise ValueError('该命令已不可用，请刷新候选')
        argv=[self.cli,'cmd','launch',command]
        if query and COMMANDS[command][2]:argv+=['--query',query]
        try:
            subprocess.run(argv,capture_output=True,text=True,timeout=6,check=True)
            status='handed_off'
        except subprocess.CalledProcessError:raise ValueError('Vicinae 拒绝了启动请求') from None
        except (OSError,subprocess.TimeoutExpired):status='outcome_unknown'
        return {'status':status,'command':command,'businessComplete':False,
                'message':'Vicinae 已受理，请在打开的界面中继续。' if status=='handed_off' else '启动结果不明，请检查 Vicinae；不会自动重试。'}

def install_vicinae(kernel,bridge):
    from .runtime.capabilities import obj,string
    id_='vicinae.launch';module='builtin.'+id_
    spec={'id':id_,'title':'打开 Vicinae 命令','module':module,'inputSchema':obj({'command':{'type':'string','enum':list(COMMANDS)},'query':string(1800)},['command','query']), 'outputSchema':{'type':'object'},'sideEffect':'L1','permissions':['desktop.launch'],'network':False,'cost':'none','reversible':True}
    manifest={'id':module,'version':'0.1.0','protocolVersion':'0.1','kind':'capability','title':spec['title'],'provides':[id_],'accepts':['command.capability.run'],'emits':['result.capability.result'],'requires_context':['intent'],'permissions':spec['permissions'],'side_effect':'L1','network':False,'cost':'none','reversible':True,'latency':'variable','trusted':True}
    def run(task,progress,cancel):
        if cancel():raise ValueError('执行已取消')
        return {'artifacts':[],**bridge.launch(task['input']['command'],task['input']['query'])}
    kernel.register(spec,manifest,run)
