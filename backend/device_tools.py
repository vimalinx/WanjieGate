"""Opt-in local tool discovery and narrowly scoped Obsidian handoff.

No browser history, note contents, or other application databases are scanned.
"""
import hashlib
import json
import re
import plistlib
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlencode, quote

CONFIG = Path.home() / 'Library/Application Support/obsidian/obsidian.json'
LOCK = threading.Lock()

def vaults(config=CONFIG):
    try:
        value=json.loads(config.read_text())
        return {key:Path(item['path']) for key,item in value.get('vaults',{}).items()
                if isinstance(item,dict) and isinstance(item.get('path'),str) and Path(item['path']).is_dir()}
    except (OSError, ValueError, TypeError):
        return {}

# Only these installed bundles can be opened. No arbitrary paths, URLs or shell arguments.
SUPPORTED={
 'chrome':{'file':'Google Chrome.app','bundle':'com.google.Chrome','name':'Chrome 网页搜索','scenes':['research','learning']},
 'chatgpt':{'file':'ChatGPT.app','bundle':'com.openai.codex','name':'ChatGPT','scenes':['development']},
 'kimi':{'file':'Kimi.app','bundle':'com.moonshot.kimichat','name':'Kimi','scenes':['research','learning','planning','writing']},
 'cursor':{'file':'Cursor.app','bundle':'com.todesktop.230313mzl4w4u92','name':'Cursor','scenes':['development']},
 'zotero':{'file':'Zotero.app','bundle':'org.zotero.zotero','name':'Zotero','scenes':['research']},
 'reminders':{'file':'Reminders.app','bundle':'com.apple.reminders','name':'提醒事项','scenes':['planning']},
 'stocks':{'file':'Stocks.app','bundle':'com.apple.stocks','name':'股市','scenes':['market']},
 'notes':{'file':'Notes.app','bundle':'com.apple.Notes','name':'备忘录','scenes':['writing','learning','planning']},
}
def app_path(key,roots):
    spec=SUPPORTED.get(key)
    if not spec:return None
    for root in roots:
        path=root/spec['file']
        try:
            info=plistlib.loads((path/'Contents/Info.plist').read_bytes())
            if info.get('CFBundleIdentifier')==spec['bundle']:return path
        except (OSError,ValueError,plistlib.InvalidFileException):pass
    return None

def roots_default():return [Path('/Applications'),Path.home()/'Applications',Path('/System/Applications')]

def discover(app_roots=None, config=CONFIG):
    roots=app_roots if app_roots is not None else roots_default()
    installed=any((root/'Obsidian.app').is_dir() for root in roots)
    apps=[{'id':key,'name':spec['name'],'scenes':spec['scenes']} for key,spec in SUPPORTED.items() if app_path(key,roots)]
    keys={a['id'] for a in apps};defaults={}
    for scene,choices in {'writing':['notes','kimi'],'research':['kimi','zotero'],'learning':['kimi','notes'],'development':['cursor'],'planning':['reminders','kimi','notes'],'market':['stocks']}.items():
        default=next((key for key in choices if key in keys),None)
        if default:defaults[scene]='app:'+default
    return {'obsidian':{'installed':installed,'vaults':[{'id':key,'name':path.name} for key,path in vaults(config).items()] if installed else []},
            'apps':apps,'defaults':defaults,'sources':['installed-supported-apps','obsidian-vault-names'], 'historyCollected':False}

def launch_app(request, app_roots=None):
    key=request.get('tool');roots=app_roots if app_roots is not None else roots_default()
    if not isinstance(key,str):raise ValueError('工具标识无效')
    path=app_path(key,roots)
    if path is None:raise ValueError('该工具未安装或不在支持列表中，请重新检测')
    args=['open','-a',str(path)];query=request.get('query','')
    if not isinstance(query,str) or len(query)>1800:raise ValueError('搜索内容无效或过长')
    search=key=='chrome' and bool(query.strip())
    if search:args.append('https://www.google.com/search?'+urlencode({'q':query},quote_via=quote))
    try:
        subprocess.run(args,check=True,timeout=10,capture_output=True)
    except (OSError,subprocess.SubprocessError):return {'status':'outcome_unknown','name':SUPPORTED[key]['name']}
    return {'status':'opened','name':SUPPORTED[key]['name'],'contentTransferred':False,'searchOpened':search}

def launch_obsidian(request, data_dir, config=CONFIG):
    vault=request.get('vault');available=vaults(config)
    if vault not in available:raise ValueError('请选择本机存在的 Obsidian 仓库')
    identity=request.get('id');content=request.get('content');title=request.get('title')
    if not all(isinstance(v,str) for v in [identity,content,title]) or not identity or len(content)>16000:
        raise ValueError('交接内容格式错误或超过 16000 字符，请改用复制内容')
    digest=hashlib.sha256(json.dumps([vault,identity,content],ensure_ascii=False).encode()).hexdigest()
    title=re.sub(r'[^\w\u4e00-\u9fff -]', '', title).strip()[:36] or '新笔记'
    file=f'万界门/{title}-{digest[:12]}.md'
    receipts=Path(data_dir)/'tool-handoffs';receipts.mkdir(parents=True,exist_ok=True)
    receipt=receipts/(digest+'.json')
    with LOCK:
        if receipt.exists():
            saved=json.loads(receipt.read_text())
            if (available[vault]/saved['file']).is_file():
                uri='obsidian://open?'+urlencode({'vault':vault,'file':saved['file'],'paneType':'tab'},quote_via=quote)
                try:
                    subprocess.run(['open','-a','Obsidian',uri],check=True,timeout=10,capture_output=True)
                except (OSError,subprocess.SubprocessError):
                    return {**saved,'reused':True,'status':'outcome_unknown'}
            return {**saved,'reused':True}
        exists=(available[vault]/file).is_file()
        params={'vault':vault,'file':file,'paneType':'tab'}
        if not exists:params['content']=content
        uri='obsidian://'+('open' if exists else 'new')+'?'+urlencode(params, quote_via=quote)
        # Reserve before dispatch: ambiguous OS failures are never automatically retried.
        result={'status':'dispatching','file':file,'vault':vault,'reused':False}
        receipt.write_text(json.dumps(result,ensure_ascii=False))
        try:
            subprocess.run(['open','-a','Obsidian',uri],check=True,timeout=10,capture_output=True)
            result['status']='handed_off'
        except (OSError,subprocess.SubprocessError):
            result['status']='outcome_unknown'
        receipt.write_text(json.dumps(result,ensure_ascii=False))
        return result
